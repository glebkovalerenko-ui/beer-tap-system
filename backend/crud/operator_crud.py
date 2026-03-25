from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import card_crud, flow_accounting_crud, incident_crud, pour_crud, shift_crud, visit_crud


SEVERITY_WEIGHT = {"critical": 0, "warning": 1, "info": 2}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _minutes_since(value: datetime | None) -> int | None:
    value = _as_utc(value)
    if value is None:
        return None
    return max(0, int((_utcnow() - value).total_seconds() // 60))


def _permissions(current_user: dict | None) -> set[str]:
    return {
        str(item).strip()
        for item in (current_user or {}).get("permissions", [])
        if str(item).strip()
    }


def _action_policy(
    current_user: dict | None,
    *,
    permission: str | None = None,
    confirm_required: bool = False,
    second_approval_required: bool = False,
    reason_code_required: bool = False,
) -> schemas.OperatorActionPolicy:
    granted = _permissions(current_user)
    allowed = True if permission is None else permission in granted
    disabled_reason = None if allowed else f"Requires permission: {permission}"
    return schemas.OperatorActionPolicy(
        allowed=allowed,
        confirm_required=confirm_required,
        second_approval_required=second_approval_required,
        reason_code_required=reason_code_required,
        disabled_reason=disabled_reason,
    )


def _tap_action_policies(current_user: dict | None) -> schemas.TapActionPolicySet:
    return schemas.TapActionPolicySet(
        open=_action_policy(current_user, permission="taps_view"),
        stop=_action_policy(current_user, permission="taps_control", confirm_required=True, reason_code_required=True),
        block=_action_policy(current_user, permission="taps_control", confirm_required=True),
        screen=_action_policy(current_user, permission="display_override"),
        keg=_action_policy(current_user, permission="taps_control"),
        history=_action_policy(current_user, permission="sessions_view"),
    )


def _contextualize_policy(
    policy: schemas.OperatorActionPolicy,
    *,
    allowed: bool,
    disabled_reason: str | None = None,
) -> schemas.OperatorActionPolicy:
    if allowed:
        return policy
    return schemas.OperatorActionPolicy(
        allowed=False,
        confirm_required=policy.confirm_required,
        second_approval_required=policy.second_approval_required,
        reason_code_required=policy.reason_code_required,
        disabled_reason=disabled_reason or policy.disabled_reason,
    )


def _normalize_completion_source(summary: schemas.SessionHistoryListItem) -> str:
    raw = str(summary.completion_source or "").strip().lower()
    actions = {
        str(action.action or "").strip().lower()
        for action in (summary.operator_actions or [])
    }

    if summary.contains_non_sale_flow:
        return "no_sale_flow"
    if raw in {"card_removed", "card_removed_close"} or "card_removed" in raw:
        return "card_removed"
    if raw in {"timeout", "timeout_close"} or raw.endswith("_timeout") or "timeout" in raw:
        return "timeout"
    if raw.startswith("blocked_") or actions.intersection({"lost_card_blocked", "insufficient_funds_blocked", "card_in_use_on_other_tap"}):
        return "blocked"
    if raw.startswith("denied_") or "insufficient_funds_denied" in actions:
        return "denied"
    if raw == "sync_pending" and summary.has_unsynced:
        return "timeout"
    if raw:
        return "normal"
    if summary.operator_status == "Прервана":
        return "blocked"
    return "" if summary.visit_status == "active" else "normal"


def _is_zero_volume_abort(summary: schemas.SessionHistoryListItem) -> bool:
    lifecycle = summary.lifecycle
    return (
        summary.operator_status == "Прервана"
        and lifecycle.first_pour_started_at is None
        and lifecycle.last_pour_ended_at is None
    )


def _safe_details(details: str | None) -> dict:
    if not details:
        return {}
    try:
        data = json.loads(details)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _guest_full_name(guest: models.Guest | None) -> str | None:
    if guest is None:
        return None
    parts = [guest.last_name, guest.first_name, guest.patronymic]
    value = " ".join(part for part in parts if part)
    return value or None


def _tap_label(*, tap_id: int | None, tap: models.Tap | None = None) -> str | None:
    if tap is not None and getattr(tap, "display_name", None):
        return tap.display_name
    if tap_id is None:
        return None
    return f"Tap {tap_id}"


def _normalized_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def _visit_canonical_status(
    *,
    visit_status: str | None,
    completion_source: str | None,
    has_incident: bool = False,
    has_unsynced: bool = False,
    active_tap_id: int | None = None,
    zero_volume_abort: bool = False,
) -> str:
    normalized_completion = _normalized_text(completion_source)
    normalized_visit_status = _normalized_text(visit_status)

    if normalized_completion == "blocked":
        return "blocked"
    if has_unsynced or has_incident or zero_volume_abort or normalized_completion in {"timeout", "denied", "no_sale_flow"}:
        return "needs_attention"
    if normalized_visit_status and normalized_visit_status != "active":
        return "completed"
    if active_tap_id is not None:
        return "pouring_now"
    return "active"


def _operator_pour_ref(kind: str, entity_id: UUID | str) -> str:
    return f"{kind}:{entity_id}"


def _parse_operator_pour_ref(pour_ref: str) -> tuple[str, str]:
    normalized = str(pour_ref or "").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="pour_ref must not be empty")
    if ":" not in normalized:
        return "pour", normalized
    kind, entity_id = normalized.split(":", 1)
    if kind not in {"pour", "flow", "audit"} or not entity_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported pour reference")
    return kind, entity_id


def _matches_operator_search_text(query: str, *values: object) -> bool:
    normalized_query = _normalized_text(query)
    if not normalized_query:
        return True
    return any(normalized_query in _normalized_text(str(value or "")) for value in values)


def _resolve_operator_search_limit(limit: int | None, *, fallback: int = 5, cap: int = 8) -> int:
    if limit is None:
        return fallback
    return max(1, min(cap, int(limit)))


def _to_operator_session_item(summary: schemas.SessionHistoryListItem) -> schemas.OperatorSessionJournalItem:
    last_operator_action = summary.operator_actions[-1] if summary.operator_actions else None
    completion_source = _normalize_completion_source(summary) or None
    return schemas.OperatorSessionJournalItem(
        **{
            **summary.model_dump(),
            "completion_source": completion_source,
        },
        canonical_visit_status=_visit_canonical_status(
            visit_status=summary.visit_status,
            completion_source=completion_source,
            has_incident=summary.has_incident,
            has_unsynced=summary.has_unsynced,
            active_tap_id=summary.primary_tap_id if summary.visit_status == "active" else None,
            zero_volume_abort=_is_zero_volume_abort(summary),
        ),
        is_active=summary.visit_status == "active",
        has_zero_volume_abort=_is_zero_volume_abort(summary),
        last_operator_action=last_operator_action,
    )


def _resolve_session_period(
    db: Session,
    filters: schemas.OperatorSessionJournalFilterParams,
) -> tuple[date | None, date | None]:
    if filters.period_preset == "range":
        return filters.date_from, filters.date_to

    if filters.period_preset == "shift":
        shift_state = shift_crud.get_current_shift_state(db)
        if shift_state.get("status") == "open" and shift_state.get("shift"):
            shift = shift_state["shift"]
            opened_at = shift.opened_at.date() if shift.opened_at else None
            closed_at = shift.closed_at.date() if shift.closed_at else _utcnow().date()
            return opened_at, closed_at

    today = _utcnow().date()
    return today, today


def _session_action_policies(
    current_user: dict | None,
    summary: schemas.OperatorSessionJournalItem,
) -> schemas.OperatorSessionActionPolicySet:
    is_active = summary.is_active
    has_card = bool(summary.card_uid)
    return schemas.OperatorSessionActionPolicySet(
        close=_contextualize_policy(
            _action_policy(
                current_user,
                permission="sessions_view",
                confirm_required=True,
                reason_code_required=True,
            ),
            allowed=is_active,
            disabled_reason="Session is already closed.",
        ),
        force_unlock=_contextualize_policy(
            _action_policy(
                current_user,
                permission="maintenance_actions",
                confirm_required=True,
                reason_code_required=True,
            ),
            allowed=is_active,
            disabled_reason="Only active sessions can be force-unlocked.",
        ),
        reconcile=_contextualize_policy(
            _action_policy(
                current_user,
                permission="maintenance_actions",
                confirm_required=True,
                reason_code_required=True,
            ),
            allowed=is_active,
            disabled_reason="Manual reconcile is only available for active sessions.",
        ),
        mark_lost_card=_contextualize_policy(
            _action_policy(
                current_user,
                permission="cards_block_manage",
                confirm_required=True,
                reason_code_required=True,
            ),
            allowed=is_active and has_card,
            disabled_reason="Active card context is required to mark a card as lost.",
        ),
    )


def _card_guest_action_policies(
    current_user: dict | None,
    *,
    guest: models.Guest | None,
    visit: models.Visit | None,
    base_resolution: dict,
) -> schemas.CardGuestActionPolicySet:
    is_lost = bool(base_resolution.get("is_lost"))
    has_lookup_uid = bool(base_resolution.get("card_uid"))
    has_visit_context = bool(
        visit is not None
        or base_resolution.get("active_visit")
        or (base_resolution.get("lost_card") or {}).get("visit_id")
    )
    can_reissue = bool(guest is not None and (is_lost or has_visit_context))

    return schemas.CardGuestActionPolicySet(
        top_up=_contextualize_policy(
            _action_policy(current_user, permission="cards_top_up"),
            allowed=guest is not None,
            disabled_reason="Guest context is required to top up balance.",
        ),
        toggle_block=_contextualize_policy(
            _action_policy(current_user, permission="cards_block_manage", confirm_required=True),
            allowed=guest is not None,
            disabled_reason="Guest context is required to change the active status.",
        ),
        mark_lost=_contextualize_policy(
            _action_policy(current_user, permission="cards_reissue_manage", confirm_required=True),
            allowed=not is_lost and has_visit_context,
            disabled_reason="An active visit is required before the card can be marked as lost."
            if not is_lost
            else "Card is already marked as lost.",
        ),
        restore_lost=_contextualize_policy(
            _action_policy(current_user, permission="cards_reissue_manage", confirm_required=True),
            allowed=is_lost,
            disabled_reason="Card is not currently marked as lost.",
        ),
        reissue=_contextualize_policy(
            _action_policy(current_user, permission="cards_reissue_manage"),
            allowed=can_reissue,
            disabled_reason="Guest context with an active or lost card workflow is required to reissue the card.",
        ),
        open_history=_contextualize_policy(
            _action_policy(current_user, permission="cards_history_view"),
            allowed=has_lookup_uid,
            disabled_reason="Card UID is required to open history.",
        ),
        open_visit=_contextualize_policy(
            _action_policy(current_user, permission="cards_open_active_session"),
            allowed=has_visit_context,
            disabled_reason="There is no active visit linked to this card.",
        ),
    )


def _format_rub(value: Decimal | None) -> str:
    if value is None:
        return "—"
    normalized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{normalized} ₽"


def _format_volume_ml(value: int | None) -> str:
    if value is None:
        return "—"
    if int(value) >= 1000:
        liters = Decimal(str(value)) / Decimal("1000")
        return f"{liters.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)} L"
    return f"{int(value)} ml"


def _device_index(system_health: dict, subsystem_name: str) -> tuple[dict[str, dict], dict | None]:
    subsystem = next(
        (item for item in system_health.get("subsystems", []) if item.get("name") == subsystem_name),
        None,
    )
    if not subsystem:
        return {}, None
    by_tap = {}
    for device in subsystem.get("devices", []):
        tap_name = device.get("tap")
        if tap_name:
            by_tap[str(tap_name)] = device
    return by_tap, subsystem


def _status_from_device(
    device: dict | None,
    *,
    fallback_state: str,
    fallback_label: str,
    fallback_detail: str | None = None,
) -> schemas.OperatorSubsystemStatus:
    if device:
        return schemas.OperatorSubsystemStatus(
            state=str(device.get("state") or fallback_state),
            label=str(device.get("label") or fallback_label),
            detail=device.get("detail") or fallback_detail,
            updated_at=device.get("updated_at"),
        )
    return schemas.OperatorSubsystemStatus(
        state=fallback_state,
        label=fallback_label,
        detail=fallback_detail,
        updated_at=None,
    )


def _controller_status(
    *,
    last_heartbeat_at: datetime | None,
    controllers_subsystem: dict | None,
    pending_sync_count: int,
) -> schemas.OperatorSubsystemStatus:
    stale_minutes = _minutes_since(last_heartbeat_at)
    if stale_minutes is not None and stale_minutes >= 15:
        return schemas.OperatorSubsystemStatus(
            state="critical",
            label="Controller heartbeat stale",
            detail=f"No heartbeat for {stale_minutes} min",
            updated_at=last_heartbeat_at,
        )
    if stale_minutes is not None and stale_minutes >= 5:
        return schemas.OperatorSubsystemStatus(
            state="warning",
            label="Controller heartbeat aging",
            detail=f"Last heartbeat {stale_minutes} min ago",
            updated_at=last_heartbeat_at,
        )
    if pending_sync_count > 0:
        return schemas.OperatorSubsystemStatus(
            state="warning",
            label="Controller waiting for sync",
            detail=f"Pending sync items: {pending_sync_count}",
            updated_at=last_heartbeat_at,
        )
    if controllers_subsystem and controllers_subsystem.get("state") in {"warning", "critical"}:
        return schemas.OperatorSubsystemStatus(
            state=str(controllers_subsystem.get("state")),
            label=str(controllers_subsystem.get("label") or "Controllers need attention"),
            detail=controllers_subsystem.get("detail"),
            updated_at=last_heartbeat_at,
        )
    return schemas.OperatorSubsystemStatus(
        state="ok",
        label="Controller responsive",
        detail="Controller runtime looks healthy for operator flow.",
        updated_at=last_heartbeat_at,
    )


def _latest_heartbeat(active_session: dict | None, recent_events: list[dict]) -> datetime | None:
    candidates: list[datetime] = []
    if active_session and active_session.get("lock_set_at"):
        lock_set_at = _as_utc(active_session.get("lock_set_at"))
        if lock_set_at is not None:
            candidates.append(lock_set_at)
    for item in recent_events:
        timestamp = _as_utc(
            item.get("timestamp")
            or item.get("ended_at")
            or item.get("started_at")
        )
        if timestamp is not None:
            candidates.append(timestamp)
    return max(candidates) if candidates else None


def _live_status(
    *,
    tap: models.Tap,
    display_enabled: bool,
    active_session: dict | None,
    sync_state: str,
) -> str:
    if active_session:
        return f"Guest {active_session.get('guest_full_name') or 'is in service flow'} on this tap right now."
    if sync_state == "syncing":
        return "Tap is waiting for backend confirmation of recent local activity."
    if not display_enabled:
        return "Guest-facing screen is disabled; operator control remains available."
    if tap.keg_id is None:
        return "Assign a keg to return this line to service."
    return "Line is quiet and ready for the next operator action."


def _build_tap_cards(
    db: Session,
    *,
    current_user: dict | None,
    tap_id: int | None = None,
) -> list[schemas.TapWorkspaceCard]:
    query = (
        db.query(models.Tap)
        .options(
            joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
            joinedload(models.Tap.display_config),
        )
        .order_by(models.Tap.tap_id.asc())
    )
    if tap_id is not None:
        query = query.filter(models.Tap.tap_id == tap_id)
    taps = query.all()
    if tap_id is not None and not taps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tap not found")

    active_visits = visit_crud.get_active_visits_list(db)
    active_by_tap = {
        int(visit["active_tap_id"]): visit
        for visit in active_visits
        if visit.get("active_tap_id") is not None
    }

    feed_items = pour_crud.get_live_feed(db, limit=max(40, len(taps) * 8 or 40))
    feed_by_tap: dict[int, list[dict]] = defaultdict(list)
    for item in feed_items:
        item_tap_id = item.get("tap_id")
        if item_tap_id is not None:
            feed_by_tap[int(item_tap_id)].append(item)

    pending_sync_rows = (
        db.query(
            models.Pour.tap_id.label("tap_id"),
            func.count(models.Pour.pour_id).label("pending_count"),
        )
        .filter(models.Pour.sync_status == "pending_sync")
        .group_by(models.Pour.tap_id)
        .all()
    )
    pending_sync_by_tap = {
        int(row.tap_id): int(row.pending_count or 0)
        for row in pending_sync_rows
    }

    system_health = incident_crud.get_system_summary(db)
    display_by_tap, _display_subsystem = _device_index(system_health, "display_agents")
    reader_by_tap, _reader_subsystem = _device_index(system_health, "readers")
    _controller_devices, controllers_subsystem = _device_index(system_health, "controllers")

    action_policies = _tap_action_policies(current_user)
    cards: list[schemas.TapWorkspaceCard] = []
    for tap in taps:
        active_session = active_by_tap.get(tap.tap_id)
        recent_events = feed_by_tap.get(tap.tap_id, [])[:10]
        last_heartbeat_at = _latest_heartbeat(active_session, recent_events)
        pending_sync_count = pending_sync_by_tap.get(tap.tap_id, 0)
        sync_state = "syncing" if pending_sync_count > 0 or tap.status == "processing_sync" else "live" if active_session else "idle"
        display_enabled = True if tap.display_config is None else bool(tap.display_config.enabled)
        display_device = display_by_tap.get(tap.display_name)
        reader_device = reader_by_tap.get(tap.display_name)
        current_event = recent_events[0] if recent_events else None

        display_status = _status_from_device(
            display_device,
            fallback_state="warning" if not display_enabled else "ok" if tap.keg_id else "warning",
            fallback_label="Guest screen disabled" if not display_enabled else "Display connected" if tap.keg_id else "Waiting for keg content",
            fallback_detail="Tap display is disabled in configuration." if not display_enabled else f"tap_status={tap.status}",
        )
        reader_status = _status_from_device(
            reader_device,
            fallback_state="busy" if active_session else "ok",
            fallback_label=f"Card {active_session.get('card_uid')}" if active_session and active_session.get("card_uid") else "Reader ready",
            fallback_detail="Guest is currently holding an active session." if active_session else f"tap_status={tap.status}",
        )

        cards.append(
            schemas.TapWorkspaceCard(
                tap_id=tap.tap_id,
                display_name=tap.display_name,
                status=tap.status,
                keg_id=tap.keg_id,
                keg=tap.keg,
                display_enabled=display_enabled,
                controller_status=_controller_status(
                    last_heartbeat_at=last_heartbeat_at,
                    controllers_subsystem=controllers_subsystem,
                    pending_sync_count=pending_sync_count,
                ),
                display_status=display_status,
                reader_status=reader_status,
                sync_state=sync_state,
                last_heartbeat_at=last_heartbeat_at,
                active_session=active_session,
                recent_events=recent_events,
                current_pour_volume_ml=int(current_event.get("volume_ml") or 0) if current_event else None,
                current_pour_amount=current_event.get("amount_charged") if current_event else None,
                live_status=_live_status(
                    tap=tap,
                    display_enabled=display_enabled,
                    active_session=active_session,
                    sync_state=sync_state,
                ),
                safe_actions=action_policies,
            )
        )
    return cards


def _tap_attention_items(cards: list[schemas.TapWorkspaceCard]) -> list[schemas.OperatorAttentionItem]:
    items: list[schemas.OperatorAttentionItem] = []
    for card in cards:
        tap_label = card.display_name
        if card.keg_id is None:
            items.append(
                schemas.OperatorAttentionItem(
                    key=f"no-keg-{card.tap_id}",
                    kind="no_keg",
                    severity="warning",
                    title=tap_label,
                    description="Tap has no keg assigned and is not sellable.",
                    action_label="Open tap",
                    target="tap",
                    href="/taps",
                    tap_id=card.tap_id,
                    category="keg",
                    system_source=tap_label,
                )
            )
        if card.sync_state == "syncing":
            items.append(
                schemas.OperatorAttentionItem(
                    key=f"sync-{card.tap_id}",
                    kind="unsynced_flow",
                    severity="warning",
                    title=tap_label,
                    description="Recent local activity is still waiting for backend confirmation.",
                    action_label="Open session",
                    target="session",
                    href="/sessions",
                    tap_id=card.tap_id,
                    visit_id=card.active_session.visit_id if card.active_session else None,
                    category="sync",
                    system_source=tap_label,
                )
            )
        for kind, status_model in (
            ("controller_offline", card.controller_status),
            ("display_offline", card.display_status),
            ("reader_offline", card.reader_status),
        ):
            if status_model.state not in {"warning", "critical", "error", "offline"}:
                continue
            items.append(
                schemas.OperatorAttentionItem(
                    key=f"{kind}-{card.tap_id}",
                    kind=kind,
                    severity="critical" if status_model.state in {"critical", "error", "offline"} else "warning",
                    title=tap_label,
                    description=status_model.detail or status_model.label,
                    action_label="Open tap",
                    target="tap",
                    href="/taps",
                    tap_id=card.tap_id,
                    category=kind.replace("_", " "),
                    system_source=tap_label,
                )
            )
    return items


def _system_attention_items(system_health: dict) -> list[schemas.OperatorAttentionItem]:
    items: list[schemas.OperatorAttentionItem] = []
    for subsystem in system_health.get("subsystems", []):
        state = str(subsystem.get("state") or "ok")
        if state not in {"warning", "critical", "error", "offline"}:
            continue
        items.append(
            schemas.OperatorAttentionItem(
                key=f"system-{subsystem.get('name')}",
                kind=f"{subsystem.get('name')}_offline",
                severity="critical" if state in {"critical", "error", "offline"} else "warning",
                title=str(subsystem.get("label") or subsystem.get("name") or "System"),
                description=str(subsystem.get("detail") or subsystem.get("label") or "Subsystem needs attention"),
                action_label="Open system",
                target="system",
                href="/system",
                category="system",
                system_source=str(subsystem.get("name") or "system"),
            )
        )
    return items


def _incident_attention_items(incidents: list[dict]) -> list[schemas.OperatorAttentionItem]:
    items: list[schemas.OperatorAttentionItem] = []
    for incident in incidents:
        if incident.get("status") == "closed":
            continue
        if incident.get("priority") not in {"critical", "high"}:
            continue
        items.append(
            schemas.OperatorAttentionItem(
                key=f"incident-{incident['incident_id']}",
                kind="incident",
                severity="critical" if incident.get("priority") == "critical" else "warning",
                title=incident.get("tap") or f"Incident {incident['incident_id']}",
                description=incident.get("note_action") or incident.get("type") or "Operator attention required.",
                action_label="Open incident",
                target="incident",
                href="/incidents",
                incident_id=incident["incident_id"],
                category="incident",
                system_source=f"incident:{incident['incident_id']}",
            )
        )
    return items


def _sort_attention_items(items: list[schemas.OperatorAttentionItem]) -> list[schemas.OperatorAttentionItem]:
    return sorted(
        items,
        key=lambda item: (
            SEVERITY_WEIGHT.get(item.severity, 9),
            str(item.title).lower(),
            str(item.key).lower(),
        ),
    )


def get_operator_sessions(
    db: Session,
    *,
    filters: schemas.OperatorSessionJournalFilterParams,
    current_user: dict | None,
) -> schemas.OperatorSessionJournalModel:
    resolved_from, resolved_to = _resolve_session_period(db, filters)
    legacy_items = visit_crud.get_session_history(
        db=db,
        date_from=resolved_from,
        date_to=resolved_to,
        tap_id=filters.tap_id,
        status=filters.status,
        card_uid=filters.card_uid,
        incident_only=filters.incident_only,
        unsynced_only=filters.unsynced_only,
    )

    operator_items: list[schemas.OperatorSessionJournalItem] = []
    for item in legacy_items:
        normalized_completion = _normalize_completion_source(item)
        zero_volume_abort = _is_zero_volume_abort(item)
        if filters.completion_source and normalized_completion != filters.completion_source:
            continue
        if filters.zero_volume_abort_only and not zero_volume_abort:
            continue
        if filters.active_only and item.visit_status != "active":
            continue
        operator_items.append(_to_operator_session_item(item))

    operator_items.sort(
        key=lambda item: (
            0 if item.is_active else 1,
            -int((_as_utc(item.last_event_at) or _utcnow()).timestamp()),
        )
    )

    pinned_active_sessions = [item for item in operator_items if item.is_active]
    journal_items = (
        pinned_active_sessions
        if filters.active_only
        else [item for item in operator_items if not item.is_active]
    )
    header = schemas.OperatorSessionJournalHeader(
        total_sessions=len(operator_items),
        active_sessions=sum(1 for item in operator_items if item.is_active),
        incident_sessions=sum(1 for item in operator_items if item.has_incident),
        unsynced_sessions=sum(1 for item in operator_items if item.has_unsynced),
        zero_volume_abort_sessions=sum(1 for item in operator_items if item.has_zero_volume_abort),
    )
    applied_filters = schemas.OperatorSessionJournalFilterParams(
        **{
            **filters.model_dump(),
            "date_from": resolved_from,
            "date_to": resolved_to,
        }
    )
    return schemas.OperatorSessionJournalModel(
        generated_at=_utcnow(),
        applied_filters=applied_filters,
        header=header,
        pinned_active_sessions=pinned_active_sessions,
        items=journal_items,
    )


def get_operator_session_detail(
    db: Session,
    *,
    visit_id,
    current_user: dict | None,
) -> schemas.OperatorSessionDetailModel:
    detail = visit_crud.get_session_history_detail(db=db, visit_id=visit_id)
    summary = _to_operator_session_item(detail)
    return schemas.OperatorSessionDetailModel(
        generated_at=_utcnow(),
        summary=summary,
        narrative=detail.narrative,
        display_context=detail.display_context,
        operator_actions=detail.operator_actions,
        safe_actions=_session_action_policies(current_user, summary),
    )


def get_operator_system_health(
    db: Session,
    *,
    current_user: dict | None,
) -> schemas.OperatorSystemHealthModel:
    summary = incident_crud.get_system_summary(db)
    subsystems = summary.get("subsystems", [])
    by_name = {str(item.get("name") or ""): item for item in subsystems}
    backend_state = str((by_name.get("backend") or {}).get("state") or "ok")
    controllers_state = str((by_name.get("controllers") or {}).get("state") or "ok")
    readers_state = str((by_name.get("readers") or {}).get("state") or "ok")
    displays_state = str((by_name.get("display_agents") or {}).get("state") or "ok")

    pending_sync_rows = (
        db.query(models.Pour)
        .filter(models.Pour.sync_status == "pending_sync")
        .all()
    )
    pending_items = len(pending_sync_rows)
    unsynced_sessions = len({str(row.visit_id) for row in pending_sync_rows if row.visit_id is not None})
    oldest_pending_age_seconds = None
    if pending_sync_rows:
        oldest_pending = min(
            (
                row.authorized_at
                or row.poured_at
                or row.created_at
                for row in pending_sync_rows
                if (row.authorized_at or row.poured_at or row.created_at) is not None
            ),
            default=None,
        )
        if oldest_pending is not None:
            oldest_pending_age_seconds = max(
                0,
                int((_utcnow() - _as_utc(oldest_pending)).total_seconds()),
            )

    stale_devices = [
        device
        for subsystem in subsystems
        for device in subsystem.get("devices", [])
        if str(device.get("state") or "ok") in {"warning", "critical", "error", "offline", "unknown", "degraded"}
    ]
    stale_summary = schemas.OperatorSystemStaleSummary(
        stale_device_count=len(stale_devices),
        stale_controller_count=sum(1 for device in stale_devices if str(device.get("device_type")) == "controller"),
        stale_reader_count=sum(1 for device in stale_devices if str(device.get("device_type")) == "reader"),
        stale_display_count=sum(1 for device in stale_devices if str(device.get("device_type")) == "display_agent"),
    )

    backend_problem = backend_state in {"warning", "critical", "error", "offline", "unknown", "degraded"}
    field_problem = any(
        state in {"warning", "critical", "error", "offline", "unknown", "degraded"}
        for state in (controllers_state, readers_state, displays_state)
    )
    if backend_problem and field_problem:
        mode = "offline"
        reason = "Backend and field devices both need attention; only cached context is reliable."
    elif backend_problem:
        mode = "backend_degraded"
        reason = "Backend freshness is degraded; critical write actions should pause until resync."
    elif field_problem:
        mode = "controller_only"
        reason = "One or more field devices need attention; operator commands can be partially blocked."
    else:
        mode = "online"
        reason = "All core operator subsystems are responding normally."

    session_mutation_blocked = mode != "online"
    blocked_reason = None if not session_mutation_blocked else "Operator actions are temporarily blocked until data is fresh again."
    blocked_actions = {
        "emergency_stop": _action_policy(current_user, permission="maintenance_actions", confirm_required=True),
        "tap_control": _contextualize_policy(
            _action_policy(current_user, permission="taps_control", confirm_required=True, reason_code_required=True),
            allowed=not session_mutation_blocked,
            disabled_reason=blocked_reason,
        ),
        "session_mutation": _contextualize_policy(
            _action_policy(current_user, permission="sessions_view", confirm_required=True, reason_code_required=True),
            allowed=not session_mutation_blocked,
            disabled_reason=blocked_reason,
        ),
        "incident_mutation": _contextualize_policy(
            _action_policy(current_user, permission="incidents_manage", confirm_required=True, reason_code_required=True),
            allowed=not session_mutation_blocked,
            disabled_reason=blocked_reason,
        ),
    }

    actionable_next_steps: list[str] = []
    if mode == "backend_degraded":
        actionable_next_steps.append("Wait for backend reconnect or trigger a manual refresh before committing risky actions.")
    if mode == "controller_only":
        actionable_next_steps.append("Open the affected tap and check controller, reader, and display state on-site.")
    if pending_items > 0:
        actionable_next_steps.append(f"Review sync backlog: {pending_items} pending items across {unsynced_sessions} sessions.")
    if stale_summary.stale_device_count > 0:
        actionable_next_steps.append(f"Inspect {stale_summary.stale_device_count} stale devices from the System panel.")
    if not actionable_next_steps:
        actionable_next_steps.append("No blocked actions right now; continue regular shift workflow.")

    return schemas.OperatorSystemHealthModel(
        **summary,
        mode=mode,
        reason=reason,
        queue_summary=schemas.OperatorSystemQueueSummary(
            pending_items=pending_items,
            unsynced_sessions=unsynced_sessions,
            oldest_pending_age_seconds=oldest_pending_age_seconds,
            retry_count=0,
        ),
        stale_summary=stale_summary,
        blocked_actions=blocked_actions,
        actionable_next_steps=actionable_next_steps,
    )


def get_operator_today(db: Session, *, current_user: dict | None) -> schemas.OperatorTodayModel:
    incidents = incident_crud.list_incidents(db, limit=20)
    tap_cards = _build_tap_cards(db, current_user=current_user)
    attention_items = _sort_attention_items(
        _incident_attention_items(incidents)
        + _tap_attention_items(tap_cards)
        + _system_attention_items(incident_crud.get_system_summary(db))
    )
    return schemas.OperatorTodayModel(
        generated_at=_utcnow(),
        current_shift=shift_crud.get_current_shift_state(db),
        today_summary=pour_crud.get_today_summary(db),
        flow_summary=flow_accounting_crud.get_flow_summary(db),
        feed_items=pour_crud.get_live_feed(db, limit=20),
        system_health=get_operator_system_health(db, current_user=current_user),
        incidents=incidents,
        attention_items=attention_items,
        priority_cta_source=attention_items[0].key if attention_items else None,
    )


def get_operator_taps(db: Session, *, current_user: dict | None) -> list[schemas.TapWorkspaceCard]:
    return _build_tap_cards(db, current_user=current_user)


def get_operator_tap_detail(db: Session, *, tap_id: int, current_user: dict | None) -> schemas.TapDrawerModel:
    card = _build_tap_cards(db, current_user=current_user, tap_id=tap_id)[0]
    return schemas.TapDrawerModel(**card.model_dump(), history_items=card.recent_events[:20])


def _lookup_guest_and_visit(db: Session, base_resolution: dict) -> tuple[models.Guest | None, models.Visit | None]:
    guest = None
    visit = None
    guest_id = (
        base_resolution.get("guest", {}) or {}
    ).get("guest_id")
    if guest_id:
        guest = db.query(models.Guest).filter(models.Guest.guest_id == guest_id).first()

    active_visit_payload = base_resolution.get("active_visit")
    if active_visit_payload and active_visit_payload.get("visit_id"):
        visit = (
            db.query(models.Visit)
            .options(joinedload(models.Visit.guest))
            .filter(models.Visit.visit_id == active_visit_payload["visit_id"])
            .first()
        )
        if guest is None and visit and visit.guest:
            guest = visit.guest

    lost_payload = base_resolution.get("lost_card")
    if guest is None and lost_payload and lost_payload.get("guest_id"):
        guest = db.query(models.Guest).filter(models.Guest.guest_id == lost_payload["guest_id"]).first()
    if visit is None and lost_payload and lost_payload.get("visit_id"):
        visit = (
            db.query(models.Visit)
            .options(joinedload(models.Visit.guest))
            .filter(models.Visit.visit_id == lost_payload["visit_id"])
            .first()
        )
        if guest is None and visit and visit.guest:
            guest = visit.guest
    return guest, visit


def _recent_pours_for_lookup(db: Session, *, guest: models.Guest | None, card_uid: str) -> list[models.Pour]:
    query = (
        db.query(models.Pour)
        .options(
            joinedload(models.Pour.tap),
            joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
        )
        .order_by(
            func.coalesce(
                models.Pour.synced_at,
                models.Pour.reconciled_at,
                models.Pour.poured_at,
                models.Pour.created_at,
            ).desc()
        )
    )
    if guest is not None:
        query = query.filter(models.Pour.guest_id == guest.guest_id)
    else:
        query = query.filter(models.Pour.card_uid == card_uid)
    return query.limit(5).all()


def _recent_transactions_for_lookup(db: Session, *, guest: models.Guest | None) -> list[models.Transaction]:
    if guest is None:
        return []
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.guest_id == guest.guest_id)
        .order_by(models.Transaction.created_at.desc())
        .limit(3)
        .all()
    )


def _lookup_recent_events(
    *,
    guest: models.Guest | None,
    visit: models.Visit | None,
    base_resolution: dict,
    pours: list[models.Pour],
    transactions: list[models.Transaction],
) -> list[schemas.CardGuestEventItem]:
    items: list[schemas.CardGuestEventItem] = []
    lost_card = base_resolution.get("lost_card")
    if lost_card:
        items.append(
            schemas.CardGuestEventItem(
                title="Card marked as lost",
                description=lost_card.get("comment") or "Card needs restore or reissue before reuse.",
                timestamp=lost_card["reported_at"],
            )
        )
    if visit is not None:
        active_tap_id = visit.active_tap_id
        items.append(
            schemas.CardGuestEventItem(
                title="Active visit is open",
                description=f"Tap lock on #{active_tap_id}." if active_tap_id is not None else "Visit is active without a tap lock right now.",
                timestamp=visit.opened_at,
            )
        )
    for pour in pours:
        tap_label = pour.tap.display_name if pour.tap else f"Tap #{pour.tap_id}"
        beverage_name = pour.beverage.name if pour.beverage else "Unknown beverage"
        items.append(
            schemas.CardGuestEventItem(
                title=f"Pour {beverage_name}",
                description=f"{tap_label} · {_format_rub(pour.amount_charged)}",
                timestamp=pour.poured_at,
            )
        )
    for transaction in transactions:
        items.append(
            schemas.CardGuestEventItem(
                title=transaction.type or "Balance operation",
                description=_format_rub(transaction.amount),
                timestamp=transaction.created_at,
            )
        )
    return sorted(items, key=lambda item: item.timestamp, reverse=True)[:6]


def _allowed_quick_actions(action_policies: schemas.CardGuestActionPolicySet) -> list[str]:
    actions: list[str] = []
    if action_policies.top_up.allowed:
        actions.append("top-up")
    if action_policies.toggle_block.allowed:
        actions.append("toggle-block")
    if action_policies.reissue.allowed:
        actions.append("reissue")
    if action_policies.open_history.allowed:
        actions.append("open-history")
    if action_policies.open_visit.allowed:
        actions.append("open-visit")
    return actions


def lookup_operator_card_context(
    db: Session,
    *,
    query: str,
    current_user: dict | None,
) -> schemas.CardGuestContextModel:
    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="query must not be empty")

    base_resolution = card_crud.resolve_card(db=db, card_uid=normalized_query)
    guest, visit = _lookup_guest_and_visit(db, base_resolution)
    pours = _recent_pours_for_lookup(db, guest=guest, card_uid=base_resolution["card_uid"])
    transactions = _recent_transactions_for_lookup(db, guest=guest)
    last_pour = pours[0] if pours else None
    last_tap_label = (
        last_pour.tap.display_name if last_pour and last_pour.tap
        else f"Tap #{visit.active_tap_id}" if visit and visit.active_tap_id is not None
        else "—"
    )

    if base_resolution.get("is_lost"):
        card_state_value = "Lost / operator help required"
        card_state_tone = "warning"
    elif base_resolution.get("active_visit"):
        card_state_value = "Card is part of an active visit"
        card_state_tone = "info"
    elif base_resolution.get("guest"):
        card_state_value = "Card is assigned to a guest"
        card_state_tone = "neutral"
    elif base_resolution.get("card"):
        card_state_value = "Card exists, guest context missing"
        card_state_tone = "warning"
    else:
        card_state_value = "Card is not registered"
        card_state_tone = "critical"

    recent_events = _lookup_recent_events(
        guest=guest,
        visit=visit,
        base_resolution=base_resolution,
        pours=pours,
        transactions=transactions,
    )
    balance_value = _format_rub(guest.balance if guest is not None else None)
    visit_id = visit.visit_id if visit is not None else (base_resolution.get("lost_card") or {}).get("visit_id")

    lookup_summary_items = [
        schemas.CardGuestSummaryItem(
            key="card-state",
            label="Card status",
            value=card_state_value,
            tone=card_state_tone,
        ),
        schemas.CardGuestSummaryItem(
            key="balance",
            label="Balance",
            value=balance_value,
            tone="warning" if guest is not None and Decimal(str(guest.balance or 0)) <= 0 else "neutral",
        ),
        schemas.CardGuestSummaryItem(
            key="active-visit",
            label="Active visit",
            value=f"#{visit_id}" if visit_id else "No active visit",
            tone="info" if visit_id else "neutral",
        ),
        schemas.CardGuestSummaryItem(
            key="last-tap",
            label="Last tap",
            value=last_tap_label,
            tone="info" if last_tap_label != "—" else "neutral",
        ),
        schemas.CardGuestSummaryItem(
            key="recent-events",
            label="Recent events",
            value=f"{len(recent_events)} events" if recent_events else "No events",
            tone="info" if recent_events else "neutral",
        ),
    ]

    active_visit_payload = None
    if base_resolution.get("active_visit"):
        active_visit_payload = schemas.CardGuestContextActiveVisit(
            **base_resolution["active_visit"],
            canonical_visit_status=_visit_canonical_status(
                visit_status=(base_resolution.get("active_visit") or {}).get("status"),
                completion_source=None,
                active_tap_id=(base_resolution.get("active_visit") or {}).get("active_tap_id"),
            ),
            balance=guest.balance if guest is not None else None,
            tap_label=f"Tap #{visit.active_tap_id}" if visit and visit.active_tap_id is not None else None,
        )

    guest_payload = None
    if base_resolution.get("guest"):
        guest_payload = schemas.CardGuestContextGuest(
            **base_resolution["guest"],
            balance=guest.balance if guest is not None else None,
        )
    action_policies = _card_guest_action_policies(
        current_user,
        guest=guest,
        visit=visit,
        base_resolution=base_resolution,
    )

    return schemas.CardGuestContextModel(
        card_uid=base_resolution["card_uid"],
        is_lost=base_resolution["is_lost"],
        lost_card=base_resolution.get("lost_card"),
        active_visit=active_visit_payload,
        guest=guest_payload,
        card=base_resolution.get("card"),
        recommended_action=base_resolution["recommended_action"],
        recent_events=recent_events,
        last_tap_label=last_tap_label,
        lookup_summary_items=lookup_summary_items,
        action_policies=action_policies,
        allowed_quick_actions=_allowed_quick_actions(action_policies),
    )


def _resolve_operator_period(
    db: Session,
    *,
    period_preset: str,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    return _resolve_session_period(
        db,
        schemas.OperatorSessionJournalFilterParams(
            period_preset=period_preset,
            date_from=date_from,
            date_to=date_to,
        ),
    )


def _apply_date_range(query, column, resolved_from: date | None, resolved_to: date | None):
    if resolved_from is not None:
        query = query.filter(func.date(column) >= resolved_from)
    if resolved_to is not None:
        query = query.filter(func.date(column) <= resolved_to)
    return query


def _load_visit_detail_map(db: Session, visit_ids: set[UUID]) -> dict[UUID, schemas.OperatorSessionDetailModel]:
    details: dict[UUID, schemas.OperatorSessionDetailModel] = {}
    for visit_id in visit_ids:
        try:
            details[visit_id] = get_operator_session_detail(db=db, visit_id=visit_id, current_user=None)
        except HTTPException:
            continue
    return details


def _match_visit_for_card_event(
    db: Session,
    *,
    card_uid: str | None,
    short_id: str | None,
    occurred_at: datetime | None,
) -> models.Visit | None:
    query = db.query(models.Visit).options(joinedload(models.Visit.guest))
    if card_uid:
        query = query.filter(models.Visit.card_uid == card_uid)
    elif short_id:
        query = query.join(models.Pour, models.Pour.visit_id == models.Visit.visit_id).filter(models.Pour.short_id == short_id)
    else:
        return None

    if occurred_at is not None:
        query = query.filter(models.Visit.opened_at <= occurred_at)
        query = query.filter(or_(models.Visit.closed_at.is_(None), models.Visit.closed_at >= occurred_at))

    return query.order_by(
        models.Visit.status.asc(),
        models.Visit.opened_at.desc(),
    ).first()


def _operator_pour_item_from_pour(
    pour: models.Pour,
    *,
    visit_detail: schemas.OperatorSessionDetailModel | None = None,
) -> schemas.OperatorPourJournalItem:
    guest = pour.guest or (pour.visit.guest if pour.visit and pour.visit.guest else None)
    visit = pour.visit
    occurred_at = _as_utc(pour.authorized_at) or _as_utc(pour.poured_at) or _as_utc(pour.created_at) or _utcnow()
    ended_at = _as_utc(pour.ended_at) or _as_utc(pour.synced_at) or _as_utc(pour.reconciled_at) or _as_utc(pour.poured_at)
    completion_reason = None
    sale_kind = "sale"
    status_value = "completed"
    has_problem = False
    sync_state = str(pour.sync_status or "not_started")

    if Decimal(str(pour.amount_charged or 0)) <= 0 and int(pour.volume_ml or 0) > 0:
        sale_kind = "non_sale"
        status_value = "non_sale"
        has_problem = True
        completion_reason = "non_sale"
    if int(pour.volume_ml or 0) <= 0:
        status_value = "zero_volume"
        has_problem = True
        completion_reason = completion_reason or "zero_volume_abort"
    if visit is not None and _normalized_text(visit.closed_reason).find("timeout") >= 0 and int(pour.volume_ml or 0) <= 0:
        status_value = "timeout"
        has_problem = True
        completion_reason = visit.closed_reason
    if sync_state == "pending_sync":
        status_value = "syncing" if status_value == "completed" else status_value
        has_problem = True
        completion_reason = completion_reason or "pending_sync"
    elif sync_state == "rejected":
        status_value = "attention"
        has_problem = True
        completion_reason = completion_reason or "sync_rejected"

    if visit_detail is not None and status_value == "completed":
        normalized_completion = _normalized_text(visit_detail.summary.completion_source)
        if normalized_completion == "denied":
            status_value = "denied"
            has_problem = True
            completion_reason = visit_detail.summary.completion_source

    return schemas.OperatorPourJournalItem(
        pour_ref=_operator_pour_ref("pour", pour.pour_id),
        source_kind="pour",
        pour_id=pour.pour_id,
        visit_id=pour.visit_id,
        guest_id=pour.guest_id,
        tap_id=pour.tap_id,
        tap_label=_tap_label(tap_id=pour.tap_id, tap=pour.tap),
        guest_full_name=_guest_full_name(guest),
        card_uid=pour.card_uid,
        beverage_name=pour.beverage.name if pour.beverage else None,
        short_id=pour.short_id,
        status=status_value,
        sale_kind=sale_kind,
        sync_state=sync_state,
        volume_ml=int(pour.volume_ml or 0),
        amount_charged=pour.amount_charged,
        started_at=_as_utc(pour.started_at),
        ended_at=ended_at,
        occurred_at=occurred_at,
        completion_reason=completion_reason,
        has_problem=has_problem,
    )


def _operator_pour_item_from_flow(
    db: Session,
    flow: models.NonSaleFlow,
) -> schemas.OperatorPourJournalItem:
    occurred_at = _as_utc(flow.finalized_at) or _as_utc(flow.last_seen_at) or _as_utc(flow.started_at) or _as_utc(flow.created_at) or _utcnow()
    matched_visit = _match_visit_for_card_event(db, card_uid=flow.card_uid, short_id=flow.short_id, occurred_at=occurred_at)
    guest = matched_visit.guest if matched_visit is not None else None
    sync_state = "accounted" if int(flow.accounted_volume_ml or 0) >= int(flow.volume_ml or 0) else "pending_sync"
    return schemas.OperatorPourJournalItem(
        pour_ref=_operator_pour_ref("flow", flow.non_sale_flow_id),
        source_kind="non_sale_flow",
        visit_id=matched_visit.visit_id if matched_visit is not None else None,
        guest_id=matched_visit.guest_id if matched_visit is not None else None,
        tap_id=flow.tap_id,
        tap_label=_tap_label(tap_id=flow.tap_id, tap=flow.tap),
        guest_full_name=_guest_full_name(guest),
        card_uid=flow.card_uid,
        beverage_name=flow.keg.beverage.name if flow.keg and flow.keg.beverage else None,
        short_id=flow.short_id,
        status="non_sale",
        sale_kind="non_sale",
        sync_state=sync_state,
        volume_ml=int(flow.volume_ml or 0),
        amount_charged=Decimal("0.00"),
        started_at=_as_utc(flow.started_at),
        ended_at=_as_utc(flow.finalized_at) or _as_utc(flow.last_seen_at),
        occurred_at=occurred_at,
        completion_reason=flow.reason,
        has_problem=True,
    )


def _operator_pour_item_from_denied_log(
    db: Session,
    log: models.AuditLog,
) -> schemas.OperatorPourJournalItem:
    details = _safe_details(log.details)
    visit = None
    visit_id = details.get("visit_id") or log.target_id
    if visit_id:
        try:
            visit = (
                db.query(models.Visit)
                .options(joinedload(models.Visit.guest))
                .filter(models.Visit.visit_id == UUID(str(visit_id)))
                .first()
            )
        except (TypeError, ValueError):
            visit = None

    tap_id_value = details.get("tap_id") or details.get("requested_tap_id")
    tap_id = int(tap_id_value) if tap_id_value not in {None, ""} else None
    tap = db.query(models.Tap).options(joinedload(models.Tap.keg).joinedload(models.Keg.beverage)).filter(models.Tap.tap_id == tap_id).first() if tap_id is not None else None
    guest = visit.guest if visit is not None else None
    completion_reason = "insufficient_funds" if log.action == "insufficient_funds_denied" else log.action
    return schemas.OperatorPourJournalItem(
        pour_ref=_operator_pour_ref("audit", log.log_id),
        source_kind="denied",
        visit_id=visit.visit_id if visit is not None else None,
        guest_id=visit.guest_id if visit is not None else None,
        tap_id=tap_id,
        tap_label=_tap_label(tap_id=tap_id, tap=tap),
        guest_full_name=_guest_full_name(guest),
        card_uid=details.get("card_uid") or (visit.card_uid if visit is not None else None),
        beverage_name=tap.keg.beverage.name if tap and tap.keg and tap.keg.beverage else None,
        status="denied",
        sale_kind="sale",
        sync_state="not_started",
        volume_ml=0,
        amount_charged=Decimal("0.00"),
        started_at=None,
        ended_at=_as_utc(log.timestamp),
        occurred_at=_as_utc(log.timestamp) or _utcnow(),
        completion_reason=completion_reason,
        has_problem=True,
    )


def _filter_operator_pour_items(
    items: list[schemas.OperatorPourJournalItem],
    *,
    filters: schemas.OperatorPourJournalFilterParams,
) -> list[schemas.OperatorPourJournalItem]:
    result = items
    if filters.guest_query:
        result = [
            item for item in result
            if _matches_operator_search_text(
                filters.guest_query,
                item.guest_full_name,
                item.card_uid,
                item.short_id,
                item.visit_id,
                item.pour_id,
            )
        ]
    if filters.status:
        normalized_status = _normalized_text(filters.status)
        result = [item for item in result if _normalized_text(item.status) == normalized_status]
    if filters.problem_only:
        result = [item for item in result if item.has_problem]
    if filters.non_sale_only:
        result = [item for item in result if item.sale_kind == "non_sale"]
    if filters.zero_volume_only:
        result = [item for item in result if item.status == "zero_volume"]
    if filters.timeout_only:
        result = [item for item in result if item.status == "timeout"]
    if filters.denied_only:
        result = [item for item in result if item.status == "denied"]
    if filters.sale_mode == "sale":
        result = [item for item in result if item.sale_kind == "sale"]
    elif filters.sale_mode == "non_sale":
        result = [item for item in result if item.sale_kind == "non_sale"]
    return result


def _operator_pour_action_policies(
    current_user: dict | None,
    summary: schemas.OperatorPourJournalItem,
) -> schemas.OperatorPourActionPolicySet:
    return schemas.OperatorPourActionPolicySet(
        open_visit=_contextualize_policy(
            _action_policy(current_user, permission="sessions_view"),
            allowed=summary.visit_id is not None,
            disabled_reason="Visit context is not available for this pour.",
        ),
        open_guest=_contextualize_policy(
            _action_policy(current_user, permission="cards_lookup"),
            allowed=summary.guest_id is not None or bool(summary.card_uid),
            disabled_reason="Guest or card context is not available for this pour.",
        ),
        open_tap=_contextualize_policy(
            _action_policy(current_user, permission="taps_view"),
            allowed=summary.tap_id is not None,
            disabled_reason="Tap context is not available for this pour.",
        ),
        reconcile=_contextualize_policy(
            _action_policy(current_user, permission="maintenance_actions", confirm_required=True, reason_code_required=True),
            allowed=summary.source_kind == "pour" and summary.visit_id is not None and summary.sync_state in {"pending_sync", "rejected"},
            disabled_reason="Manual reconcile is only available for sale pours waiting for sync review.",
        ),
    )


def get_operator_pours(
    db: Session,
    *,
    filters: schemas.OperatorPourJournalFilterParams,
    current_user: dict | None,
) -> schemas.OperatorPourJournalModel:
    resolved_from, resolved_to = _resolve_operator_period(
        db,
        period_preset=filters.period_preset,
        date_from=filters.date_from,
        date_to=filters.date_to,
    )

    pour_query = (
        db.query(models.Pour)
        .options(
            joinedload(models.Pour.guest),
            joinedload(models.Pour.tap).joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
            joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
            joinedload(models.Pour.visit).joinedload(models.Visit.guest),
        )
    )
    pour_query = _apply_date_range(
        pour_query,
        func.coalesce(models.Pour.authorized_at, models.Pour.poured_at, models.Pour.created_at),
        resolved_from,
        resolved_to,
    )
    if filters.tap_id is not None:
        pour_query = pour_query.filter(models.Pour.tap_id == filters.tap_id)
    if filters.visit_id is not None:
        pour_query = pour_query.filter(models.Pour.visit_id == filters.visit_id)
    if filters.guest_query:
        pattern = f"%{filters.guest_query.strip().lower()}%"
        pour_query = pour_query.join(models.Guest, models.Pour.guest_id == models.Guest.guest_id).filter(
            or_(
                func.lower(models.Guest.last_name).like(pattern),
                func.lower(models.Guest.first_name).like(pattern),
                func.lower(models.Guest.patronymic).like(pattern),
                func.lower(models.Guest.phone_number).like(pattern),
                func.lower(models.Pour.card_uid).like(pattern),
                func.lower(func.coalesce(models.Pour.short_id, "")).like(pattern),
                cast(models.Pour.visit_id, String).ilike(pattern),
            )
        )
    pours = (
        pour_query
        .order_by(func.coalesce(models.Pour.authorized_at, models.Pour.poured_at, models.Pour.created_at).desc())
        .limit(250)
        .all()
    )

    visit_detail_map = _load_visit_detail_map(db, {pour.visit_id for pour in pours if pour.visit_id is not None})
    items = [
        _operator_pour_item_from_pour(
            pour,
            visit_detail=visit_detail_map.get(pour.visit_id) if pour.visit_id is not None else None,
        )
        for pour in pours
    ]

    if filters.sale_mode != "sale" or filters.non_sale_only:
        flow_query = (
            db.query(models.NonSaleFlow)
            .options(
                joinedload(models.NonSaleFlow.tap).joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
                joinedload(models.NonSaleFlow.keg).joinedload(models.Keg.beverage),
            )
        )
        flow_query = _apply_date_range(
            flow_query,
            func.coalesce(models.NonSaleFlow.finalized_at, models.NonSaleFlow.last_seen_at, models.NonSaleFlow.created_at),
            resolved_from,
            resolved_to,
        )
        if filters.tap_id is not None:
            flow_query = flow_query.filter(models.NonSaleFlow.tap_id == filters.tap_id)
        flows = (
            flow_query
            .order_by(func.coalesce(models.NonSaleFlow.finalized_at, models.NonSaleFlow.last_seen_at, models.NonSaleFlow.created_at).desc())
            .limit(150)
            .all()
        )
        items.extend(_operator_pour_item_from_flow(db, flow) for flow in flows)

    if filters.sale_mode != "non_sale" and not filters.non_sale_only:
        denied_logs_query = (
            db.query(models.AuditLog)
            .filter(models.AuditLog.target_entity == "Visit")
            .filter(models.AuditLog.action.in_(("insufficient_funds_denied", "card_in_use_on_other_tap")))
        )
        denied_logs_query = _apply_date_range(denied_logs_query, models.AuditLog.timestamp, resolved_from, resolved_to)
        denied_logs = denied_logs_query.order_by(models.AuditLog.timestamp.desc()).limit(150).all()
        items.extend(_operator_pour_item_from_denied_log(db, log) for log in denied_logs)

    items = _filter_operator_pour_items(items, filters=filters)
    items.sort(key=lambda item: -int((_as_utc(item.occurred_at) or _utcnow()).timestamp()))

    header = schemas.OperatorPourJournalHeader(
        total_pours=len(items),
        problem_pours=sum(1 for item in items if item.has_problem),
        sale_pours=sum(1 for item in items if item.sale_kind == "sale"),
        non_sale_pours=sum(1 for item in items if item.sale_kind == "non_sale"),
        denied_pours=sum(1 for item in items if item.status == "denied"),
        zero_volume_pours=sum(1 for item in items if item.status == "zero_volume"),
        timeout_pours=sum(1 for item in items if item.status == "timeout"),
    )
    applied_filters = schemas.OperatorPourJournalFilterParams(
        **{
            **filters.model_dump(),
            "date_from": resolved_from,
            "date_to": resolved_to,
        }
    )
    return schemas.OperatorPourJournalModel(
        generated_at=_utcnow(),
        applied_filters=applied_filters,
        header=header,
        items=items,
    )


def _operator_pour_display_context(
    db: Session,
    *,
    visit_id: UUID | None,
    tap_id: int | None,
) -> schemas.SessionDisplayContext | None:
    if visit_id is not None:
        try:
            detail = visit_crud.get_session_history_detail(db=db, visit_id=visit_id)
            return detail.display_context
        except HTTPException:
            return None
    derive_display_context = getattr(visit_crud, "_derive_display_context", None)
    if tap_id is not None and callable(derive_display_context):
        return derive_display_context(db, tap_id=tap_id, has_incident=False, incident_count=0)
    return None


def get_operator_pour_detail(
    db: Session,
    *,
    pour_ref: str,
    current_user: dict | None,
) -> schemas.OperatorPourDetailModel:
    source_kind, entity_id = _parse_operator_pour_ref(pour_ref)

    if source_kind == "pour":
        pour = (
            db.query(models.Pour)
            .options(
                joinedload(models.Pour.guest),
                joinedload(models.Pour.tap).joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
                joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
                joinedload(models.Pour.visit).joinedload(models.Visit.guest),
            )
            .filter(models.Pour.pour_id == UUID(entity_id))
            .first()
        )
        if pour is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pour not found")
        visit_detail = get_operator_session_detail(db=db, visit_id=pour.visit_id, current_user=current_user) if pour.visit_id is not None else None
        summary = _operator_pour_item_from_pour(pour, visit_detail=visit_detail)
        lifecycle = [
            schemas.OperatorPourLifecycleItem(key="authorize", label="Authorize", timestamp=_as_utc(pour.authorized_at), status="done" if pour.authorized_at else "pending", value=pour.card_uid or None),
            schemas.OperatorPourLifecycleItem(key="start", label="Start", timestamp=_as_utc(pour.started_at), status="done" if pour.started_at else ("warning" if summary.status in {"zero_volume", "timeout"} else "pending"), value=_tap_label(tap_id=pour.tap_id, tap=pour.tap)),
            schemas.OperatorPourLifecycleItem(key="stop", label="Stop", timestamp=summary.ended_at, status="warning" if summary.status in {"zero_volume", "timeout", "attention"} else "done", value=summary.completion_reason or summary.status),
            schemas.OperatorPourLifecycleItem(key="sync", label="Sync", timestamp=_as_utc(pour.synced_at) or _as_utc(pour.reconciled_at), status="done" if summary.sync_state in {"synced", "reconciled"} else ("warning" if summary.sync_state in {"pending_sync", "rejected"} else "info"), value=summary.sync_state),
        ]
        operator_actions = visit_detail.operator_actions if visit_detail is not None else []
    elif source_kind == "flow":
        flow = (
            db.query(models.NonSaleFlow)
            .options(
                joinedload(models.NonSaleFlow.tap).joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
                joinedload(models.NonSaleFlow.keg).joinedload(models.Keg.beverage),
            )
            .filter(models.NonSaleFlow.non_sale_flow_id == UUID(entity_id))
            .first()
        )
        if flow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Non-sale flow not found")
        summary = _operator_pour_item_from_flow(db, flow)
        lifecycle = [
            schemas.OperatorPourLifecycleItem(key="reader", label="Card present", timestamp=summary.started_at, status="info", value="yes" if flow.card_present else "no"),
            schemas.OperatorPourLifecycleItem(key="start", label="Start", timestamp=summary.started_at, status="done" if summary.started_at else "warning", value=flow.session_state),
            schemas.OperatorPourLifecycleItem(key="stop", label="Finalize", timestamp=summary.ended_at, status="warning", value=flow.reason),
            schemas.OperatorPourLifecycleItem(key="sync", label="Accounting", timestamp=_as_utc(flow.finalized_at) or _as_utc(flow.last_seen_at), status="done" if summary.sync_state == "accounted" else "warning", value=summary.sync_state),
        ]
        operator_actions = []
    else:
        log = db.query(models.AuditLog).filter(models.AuditLog.log_id == UUID(entity_id)).first()
        if log is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Denied pour event not found")
        summary = _operator_pour_item_from_denied_log(db, log)
        lifecycle = [
            schemas.OperatorPourLifecycleItem(key="authorize", label="Authorize attempt", timestamp=_as_utc(log.timestamp), status="critical", value=summary.card_uid or None),
            schemas.OperatorPourLifecycleItem(key="deny", label="Denied", timestamp=_as_utc(log.timestamp), status="critical", value=summary.completion_reason),
        ]
        operator_actions = []

    return schemas.OperatorPourDetailModel(
        generated_at=_utcnow(),
        summary=summary,
        lifecycle=lifecycle,
        display_context=_operator_pour_display_context(db, visit_id=summary.visit_id, tap_id=summary.tap_id),
        operator_actions=operator_actions,
        safe_actions=_operator_pour_action_policies(current_user, summary),
    )


def search_operator_workspace(
    db: Session,
    *,
    query: str,
    current_user: dict | None,
    limit: int | None = None,
) -> schemas.OperatorSearchModel:
    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="query must not be empty")

    resolved_limit = _resolve_operator_search_limit(limit)
    pattern = f"%{normalized_query.lower()}%"

    guest_rows = (
        db.query(models.Guest)
        .filter(
            or_(
                func.lower(models.Guest.last_name).like(pattern),
                func.lower(models.Guest.first_name).like(pattern),
                func.lower(models.Guest.patronymic).like(pattern),
                func.lower(models.Guest.phone_number).like(pattern),
            )
        )
        .order_by(models.Guest.updated_at.desc(), models.Guest.created_at.desc())
        .limit(resolved_limit)
        .all()
    )
    guest_items = [
        schemas.OperatorSearchResultItem(
            key=f"guest:{guest.guest_id}",
            kind="guest",
            title=_guest_full_name(guest) or guest.phone_number,
            subtitle=guest.phone_number,
            meta=f"Balance {_format_rub(guest.balance)}",
            route="guests",
            href=f"/guests?guest={guest.guest_id}",
            guest_id=guest.guest_id,
        )
        for guest in guest_rows
    ]

    visit_rows = (
        db.query(models.Visit)
        .options(joinedload(models.Visit.guest))
        .join(models.Guest, models.Visit.guest_id == models.Guest.guest_id)
        .filter(
            or_(
                func.lower(models.Guest.last_name).like(pattern),
                func.lower(models.Guest.first_name).like(pattern),
                func.lower(models.Guest.patronymic).like(pattern),
                func.lower(models.Guest.phone_number).like(pattern),
                func.lower(func.coalesce(models.Visit.card_uid, "")).like(pattern),
                cast(models.Visit.visit_id, String).ilike(pattern),
            )
        )
        .order_by(models.Visit.status.asc(), models.Visit.opened_at.desc())
        .limit(resolved_limit)
        .all()
    )
    visit_items: list[schemas.OperatorSearchResultItem] = []
    for visit in visit_rows:
        summary = _to_operator_session_item(visit_crud._build_session_history_item(db, visit, include_narrative=False))
        visit_items.append(
            schemas.OperatorSearchResultItem(
                key=f"visit:{visit.visit_id}",
                kind="visit",
                title=_guest_full_name(visit.guest) or str(visit.visit_id),
                subtitle=visit.card_uid or str(visit.visit_id),
                meta=summary.operator_status,
                route="visits",
                href=f"/visits?visit={visit.visit_id}",
                guest_id=visit.guest_id,
                visit_id=visit.visit_id,
                canonical_visit_status=summary.canonical_visit_status,
            )
        )

    tap_rows = (
        db.query(models.Tap)
        .options(joinedload(models.Tap.keg).joinedload(models.Keg.beverage))
        .outerjoin(models.Keg, models.Tap.keg_id == models.Keg.keg_id)
        .outerjoin(models.Beverage, models.Keg.beverage_id == models.Beverage.beverage_id)
        .filter(
            or_(
                cast(models.Tap.tap_id, String).ilike(pattern),
                func.lower(models.Tap.display_name).like(pattern),
                func.lower(func.coalesce(models.Beverage.name, "")).like(pattern),
            )
        )
        .order_by(models.Tap.tap_id.asc())
        .limit(resolved_limit)
        .all()
    )
    tap_items = [
        schemas.OperatorSearchResultItem(
            key=f"tap:{tap.tap_id}",
            kind="tap",
            title=tap.display_name,
            subtitle=tap.keg.beverage.name if tap.keg and tap.keg.beverage else "No beverage",
            meta=tap.status,
            route="taps",
            href=f"/taps?tap={tap.tap_id}",
            tap_id=tap.tap_id,
        )
        for tap in tap_rows
    ]

    card_rows = (
        db.query(models.Card, models.Guest, models.LostCard)
        .outerjoin(models.Guest, models.Card.guest_id == models.Guest.guest_id)
        .outerjoin(models.LostCard, models.LostCard.card_uid == models.Card.card_uid)
        .filter(
            or_(
                func.lower(models.Card.card_uid).like(pattern),
                func.lower(func.coalesce(models.Guest.last_name, "")).like(pattern),
                func.lower(func.coalesce(models.Guest.first_name, "")).like(pattern),
                func.lower(func.coalesce(models.Guest.phone_number, "")).like(pattern),
            )
        )
        .order_by(models.Card.created_at.desc())
        .limit(resolved_limit)
        .all()
    )
    card_items = [
        schemas.OperatorSearchResultItem(
            key=f"card:{card.card_uid}",
            kind="card",
            title=card.card_uid,
            subtitle=_guest_full_name(guest) if guest is not None else "Unassigned card",
            meta="Lost card" if lost_card is not None or card.status == "lost" else card.status,
            route="guests",
            href=f"/guests?card={card.card_uid}",
            guest_id=guest.guest_id if guest is not None else None,
            card_uid=card.card_uid,
        )
        for card, guest, lost_card in card_rows
    ]

    pour_rows = (
        db.query(models.Pour)
        .options(
            joinedload(models.Pour.guest),
            joinedload(models.Pour.tap).joinedload(models.Tap.keg).joinedload(models.Keg.beverage),
            joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
            joinedload(models.Pour.visit).joinedload(models.Visit.guest),
        )
        .join(models.Guest, models.Pour.guest_id == models.Guest.guest_id)
        .filter(
            or_(
                func.lower(func.coalesce(models.Pour.short_id, "")).like(pattern),
                func.lower(models.Pour.card_uid).like(pattern),
                cast(models.Pour.visit_id, String).ilike(pattern),
                func.lower(models.Guest.last_name).like(pattern),
                func.lower(models.Guest.first_name).like(pattern),
                func.lower(models.Guest.phone_number).like(pattern),
            )
        )
        .order_by(func.coalesce(models.Pour.authorized_at, models.Pour.poured_at, models.Pour.created_at).desc())
        .limit(resolved_limit)
        .all()
    )
    pour_items = [
        schemas.OperatorSearchResultItem(
            key=item.pour_ref,
            kind="pour",
            title=item.beverage_name or item.short_id or item.pour_ref,
            subtitle=item.guest_full_name or item.card_uid or "Unknown guest",
            meta=f"{item.tap_label or 'Tap'} · {item.status}",
            route="pours",
            href=f"/pours?pour={item.pour_ref}",
            guest_id=item.guest_id,
            visit_id=item.visit_id,
            tap_id=item.tap_id,
            card_uid=item.card_uid,
            pour_ref=item.pour_ref,
        )
        for item in (_operator_pour_item_from_pour(row) for row in pour_rows)
    ]

    keg_rows = (
        db.query(models.Keg)
        .options(joinedload(models.Keg.beverage), joinedload(models.Keg.tap))
        .join(models.Beverage, models.Keg.beverage_id == models.Beverage.beverage_id)
        .filter(
            or_(
                cast(models.Keg.keg_id, String).ilike(pattern),
                func.lower(models.Beverage.name).like(pattern),
                func.lower(func.coalesce(models.Beverage.style, "")).like(pattern),
                func.lower(func.coalesce(models.Beverage.brewery, "")).like(pattern),
            )
        )
        .order_by(models.Keg.created_at.desc())
        .limit(resolved_limit)
        .all()
    )
    keg_items = [
        schemas.OperatorSearchResultItem(
            key=f"keg:{keg.keg_id}",
            kind="keg",
            title=keg.beverage.name if keg.beverage else str(keg.keg_id),
            subtitle=f"Keg {keg.keg_id}",
            meta=f"{keg.status} · {_format_volume_ml(int(keg.current_volume_ml or 0))}",
            route="kegs-beverages",
            href=f"/kegs-beverages?tab=kegs&keg={keg.keg_id}",
            tap_id=keg.tap.tap_id if keg.tap is not None else None,
            keg_id=keg.keg_id,
        )
        for keg in keg_rows
    ]

    groups = [
        schemas.OperatorSearchGroup(key="guests", label="Guests", items=guest_items),
        schemas.OperatorSearchGroup(key="visits", label="Visits", items=visit_items),
        schemas.OperatorSearchGroup(key="taps", label="Taps", items=tap_items),
        schemas.OperatorSearchGroup(key="cards", label="Cards", items=card_items),
        schemas.OperatorSearchGroup(key="pours", label="Pours", items=pour_items),
        schemas.OperatorSearchGroup(key="kegs", label="Kegs", items=keg_items),
    ]
    total_results = sum(len(group.items) for group in groups)
    return schemas.OperatorSearchModel(
        generated_at=_utcnow(),
        query=normalized_query,
        total_results=total_results,
        groups=[group for group in groups if group.items],
    )
