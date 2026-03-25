from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func
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


def _format_rub(value: Decimal | None) -> str:
    if value is None:
        return "—"
    normalized = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{normalized} ₽"


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
        system_health=incident_crud.get_system_summary(db),
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


def _allowed_quick_actions(
    current_user: dict | None,
    *,
    guest: models.Guest | None,
    visit: models.Visit | None,
    base_resolution: dict,
) -> list[str]:
    granted = _permissions(current_user)
    actions: list[str] = []
    if guest is not None and "cards_top_up" in granted:
        actions.append("top-up")
    if guest is not None and "cards_block_manage" in granted:
        actions.append("toggle-block")
    if guest is not None and "cards_reissue_manage" in granted and (
        base_resolution.get("is_lost")
        or visit is not None
        or base_resolution.get("active_visit") is not None
    ):
        actions.append("reissue")
    if base_resolution.get("card_uid") and "cards_history_view" in granted:
        actions.append("open-history")
    if (visit is not None or (base_resolution.get("lost_card") or {}).get("visit_id")) and "cards_open_active_session" in granted:
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
            balance=guest.balance if guest is not None else None,
            tap_label=f"Tap #{visit.active_tap_id}" if visit and visit.active_tap_id is not None else None,
        )

    guest_payload = None
    if base_resolution.get("guest"):
        guest_payload = schemas.CardGuestContextGuest(
            **base_resolution["guest"],
            balance=guest.balance if guest is not None else None,
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
        allowed_quick_actions=_allowed_quick_actions(
            current_user,
            guest=guest,
            visit=visit,
            base_resolution=base_resolution,
        ),
    )
