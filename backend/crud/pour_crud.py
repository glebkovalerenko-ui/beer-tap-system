from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import controller_crud, visit_crud
from pos_adapter import get_pos_adapter


def _result(status: str, outcome: str, reason: str) -> dict:
    return {"status": status, "outcome": outcome, "reason": reason}


def _add_audit_log(
    db: Session,
    *,
    actor_id: str,
    action: str,
    target_entity: str,
    target_id: str,
    details: dict,
):
    db.add(
        models.AuditLog(
            actor_id=actor_id,
            action=action,
            target_entity=target_entity,
            target_id=target_id,
            details=json.dumps(details, ensure_ascii=False),
        )
    )


def _clear_active_visit_lock(*, active_visit: models.Visit, tap: models.Tap | None, keg: models.Keg | None) -> None:
    active_visit.active_tap_id = None
    active_visit.lock_set_at = None

    if tap is None:
        return

    if keg is not None and keg.current_volume_ml <= 0:
        keg.status = "empty"
        tap.status = "empty"
        keg.finished_at = func.now()
        return

    if tap.status == "processing_sync":
        tap.status = "active"


def _finalize_rejected_pending_pour(
    db: Session,
    *,
    pending_pour: models.Pour,
    active_visit: models.Visit,
    tap: models.Tap,
    keg: models.Keg,
    pour_data: schemas.PourData,
    duration_ms: int,
    actor_id: str,
    audit_action: str,
    audit_details: dict,
    reason: str,
    outcome: str,
) -> dict:
    pending_pour.client_tx_id = pour_data.client_tx_id
    pending_pour.card_uid = pour_data.card_uid
    pending_pour.tap_id = pour_data.tap_id
    pending_pour.visit_id = active_visit.visit_id
    pending_pour.volume_ml = pour_data.volume_ml
    pending_pour.poured_at = func.now()
    pending_pour.amount_charged = Decimal("0.00")
    pending_pour.duration_ms = duration_ms
    pending_pour.guest_id = active_visit.guest_id
    pending_pour.keg_id = keg.keg_id
    pending_pour.sync_status = "rejected"
    pending_pour.synced_at = None
    pending_pour.reconciled_at = None
    pending_pour.short_id = pour_data.short_id
    pending_pour.is_manual_reconcile = False

    _clear_active_visit_lock(active_visit=active_visit, tap=tap, keg=keg)
    _add_audit_log(
        db,
        actor_id=actor_id,
        action=audit_action,
        target_entity="Visit",
        target_id=str(active_visit.visit_id),
        details=audit_details,
    )
    return _result("rejected", outcome, reason)


def _resolve_duration_ms(pour_data: schemas.PourData) -> int | None:
    if pour_data.duration_ms is not None:
        return int(pour_data.duration_ms)
    if pour_data.start_ts is None or pour_data.end_ts is None:
        return None

    return int((pour_data.end_ts - pour_data.start_ts).total_seconds() * 1000)


def get_pour_by_client_tx_id(db: Session, client_tx_id: str):
    return db.query(models.Pour).filter(models.Pour.client_tx_id == client_tx_id).first()


def get_manual_pour_by_visit_short_id(db: Session, visit_id: uuid.UUID, short_id: str):
    return (
        db.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.short_id == short_id,
            models.Pour.is_manual_reconcile.is_(True),
        )
        .first()
    )


def get_pending_pour_for_visit_tap(db: Session, visit_id: uuid.UUID, tap_id: int):
    return (
        db.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
            models.Pour.is_manual_reconcile.is_(False),
        )
        .order_by(models.Pour.created_at.desc())
        .first()
    )


def _create_pour_record(
    db: Session,
    *,
    pour_data: schemas.PourData,
    duration_ms: int,
    guest_id: uuid.UUID,
    visit_id: uuid.UUID,
    keg_id: uuid.UUID,
    amount_charged: Decimal,
    price_per_ml: Decimal,
    sync_status: str,
    is_manual_reconcile: bool = False,
):
    db_pour = models.Pour(
        client_tx_id=pour_data.client_tx_id,
        card_uid=pour_data.card_uid,
        tap_id=pour_data.tap_id,
        visit_id=visit_id,
        volume_ml=pour_data.volume_ml,
        poured_at=func.now(),
        amount_charged=amount_charged,
        price_per_ml_at_pour=price_per_ml,
        duration_ms=duration_ms,
        guest_id=guest_id,
        keg_id=keg_id,
        sync_status=sync_status,
        synced_at=func.now() if sync_status == "synced" else None,
        reconciled_at=func.now() if sync_status == "reconciled" else None,
        short_id=pour_data.short_id,
        is_manual_reconcile=is_manual_reconcile,
    )
    db.add(db_pour)
    return db_pour


def process_pour(db: Session, pour_data: schemas.PourData):
    duration_ms = _resolve_duration_ms(pour_data)
    if duration_ms is None or duration_ms < 0:
        return _result(
            "rejected",
            "rejected_invalid_duration",
            "Invalid duration: provide duration_ms or valid start_ts/end_ts.",
        )

    card = (
        db.query(models.Card)
        .options(joinedload(models.Card.guest))
        .filter(models.Card.card_uid == pour_data.card_uid)
        .first()
    )
    tap = (
        db.query(models.Tap)
        .options(joinedload(models.Tap.keg).joinedload(models.Keg.beverage))
        .filter(models.Tap.tap_id == pour_data.tap_id)
        .first()
    )

    if not (card and card.guest and tap and tap.keg and tap.keg.beverage):
        return _result(
            "rejected",
            "rejected_invalid_card_or_tap",
            f"Invalid data: Card UID {pour_data.card_uid} or Tap ID {pour_data.tap_id} not found or not fully configured.",
        )

    guest = card.guest
    keg = tap.keg
    beverage = keg.beverage

    if not guest.is_active or card.status != "active":
        return _result(
            "rejected",
            "rejected_inactive_guest_or_card",
            f"Guest {guest.guest_id} or Card {card.card_uid} is not active.",
        )

    active_visit = visit_crud.get_active_visit_by_card_uid(db=db, card_uid=card.card_uid)
    if not active_visit:
        return _result(
            "rejected",
            "rejected_no_active_visit",
            f"No active visit for Card {card.card_uid}.",
        )

    # No double charge path: lock was already cleared (manual reconcile or prior accept).
    if active_visit.active_tap_id is None:
        matched_manual = get_manual_pour_by_visit_short_id(
            db=db,
            visit_id=active_visit.visit_id,
            short_id=pour_data.short_id,
        )
        if matched_manual:
            _add_audit_log(
                db,
                actor_id="internal_rpi",
                action="late_sync_matched",
                target_entity="Visit",
                target_id=str(active_visit.visit_id),
                details={
                    "short_id": pour_data.short_id,
                    "client_tx_id": pour_data.client_tx_id,
                    "manual_pour_id": str(matched_manual.pour_id),
                    "tap_id": pour_data.tap_id,
                },
            )
            return _result("audit_only", "audit_late_matched", "late_sync_matched")

        _add_audit_log(
            db,
            actor_id="internal_rpi",
            action="late_sync_mismatch",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "short_id": pour_data.short_id,
                "client_tx_id": pour_data.client_tx_id,
                "tap_id": pour_data.tap_id,
                "volume_ml": pour_data.volume_ml,
                "price_cents": pour_data.price_cents,
                "duration_ms": duration_ms,
            },
        )
        return _result("audit_only", "audit_late_recorded", "late_sync_mismatch_recorded")

    if active_visit.active_tap_id != pour_data.tap_id:
        _add_audit_log(
            db,
            actor_id="internal_rpi",
            action="sync_conflict",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": card.card_uid,
                "requested_tap_id": pour_data.tap_id,
                "active_tap_id": active_visit.active_tap_id,
                "client_tx_id": pour_data.client_tx_id,
                "short_id": pour_data.short_id,
                "duration_ms": duration_ms,
            },
        )
        return _result(
            "conflict",
            "rejected_tap_mismatch",
            f"Card already in use on Tap {active_visit.active_tap_id}",
        )

    if tap.status not in {"active", "processing_sync"} or keg.status != "in_use":
        return _result(
            "rejected",
            "rejected_tap_or_keg_state",
            f"Tap {tap.tap_id} or Keg {keg.keg_id} is not in 'active/processing_sync'/'in_use' state.",
        )

    pending_pour = get_pending_pour_for_visit_tap(db=db, visit_id=active_visit.visit_id, tap_id=pour_data.tap_id)
    if not pending_pour:
        _add_audit_log(
            db,
            actor_id="internal_rpi",
            action="sync_missing_pending",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": card.card_uid,
                "guest_id": str(guest.guest_id),
                "tap_id": pour_data.tap_id,
                "client_tx_id": pour_data.client_tx_id,
                "short_id": pour_data.short_id,
                "volume_ml": pour_data.volume_ml,
                "duration_ms": duration_ms,
            },
        )
        _clear_active_visit_lock(active_visit=active_visit, tap=tap, keg=keg)
        return _result("audit_only", "audit_missing_pending", "missing_pending_authorize")

    if int(pour_data.volume_ml) <= 0:
        return _finalize_rejected_pending_pour(
            db,
            pending_pour=pending_pour,
            active_visit=active_visit,
            tap=tap,
            keg=keg,
            pour_data=pour_data,
            duration_ms=duration_ms,
            actor_id="internal_rpi",
            audit_action="sync_rejected_zero_volume",
            audit_details={
                "card_uid": card.card_uid,
                "guest_id": str(guest.guest_id),
                "tap_id": pour_data.tap_id,
                "client_tx_id": pour_data.client_tx_id,
                "short_id": pour_data.short_id,
                "volume_ml": int(pour_data.volume_ml),
                "duration_ms": duration_ms,
            },
            reason="zero_volume_session",
            outcome="rejected_zero_volume",
        )

    price_per_ml = pending_pour.price_per_ml_at_pour
    if price_per_ml is None or price_per_ml <= 0:
        price_per_ml = beverage.sell_price_per_liter / Decimal(1000)
    tail_volume_ml = min(max(int(getattr(pour_data, "tail_volume_ml", 0) or 0), 0), int(pour_data.volume_ml))
    non_tail_volume_ml = max(int(pour_data.volume_ml) - tail_volume_ml, 0)
    amount_to_charge = (Decimal(pour_data.volume_ml) * price_per_ml).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    non_tail_amount_to_charge = (Decimal(non_tail_volume_ml) * price_per_ml).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if guest.balance < amount_to_charge:
        if tail_volume_ml > 0 and guest.balance >= non_tail_amount_to_charge:
            _add_audit_log(
                db,
                actor_id="internal_rpi",
                action="sync_tail_overdraft_accepted",
                target_entity="Visit",
                target_id=str(active_visit.visit_id),
                details={
                    "card_uid": card.card_uid,
                    "guest_id": str(guest.guest_id),
                    "tap_id": pour_data.tap_id,
                    "client_tx_id": pour_data.client_tx_id,
                    "short_id": pour_data.short_id,
                    "volume_ml": pour_data.volume_ml,
                    "tail_volume_ml": tail_volume_ml,
                    "balance_before_charge": str(guest.balance),
                    "non_tail_amount_to_charge": str(non_tail_amount_to_charge),
                    "amount_to_charge": str(amount_to_charge),
                },
            )
        else:
            return _finalize_rejected_pending_pour(
                db,
                pending_pour=pending_pour,
                active_visit=active_visit,
                tap=tap,
                keg=keg,
                pour_data=pour_data,
                duration_ms=duration_ms,
                actor_id="internal_rpi",
                audit_action="sync_rejected_insufficient_funds",
                audit_details={
                    "card_uid": card.card_uid,
                    "guest_id": str(guest.guest_id),
                    "tap_id": pour_data.tap_id,
                    "client_tx_id": pour_data.client_tx_id,
                    "short_id": pour_data.short_id,
                    "volume_ml": pour_data.volume_ml,
                    "tail_volume_ml": tail_volume_ml,
                    "balance_before_charge": str(guest.balance),
                    "non_tail_amount_to_charge": str(non_tail_amount_to_charge),
                    "amount_to_charge": str(amount_to_charge),
                },
                reason="insufficient_funds",
                outcome="rejected_insufficient_funds",
            )

    if keg.current_volume_ml < pour_data.volume_ml:
        return _finalize_rejected_pending_pour(
            db,
            pending_pour=pending_pour,
            active_visit=active_visit,
            tap=tap,
            keg=keg,
            pour_data=pour_data,
            duration_ms=duration_ms,
            actor_id="internal_rpi",
            audit_action="sync_rejected_insufficient_keg_volume",
            audit_details={
                "card_uid": card.card_uid,
                "guest_id": str(guest.guest_id),
                "tap_id": pour_data.tap_id,
                "client_tx_id": pour_data.client_tx_id,
                "short_id": pour_data.short_id,
                "volume_ml": pour_data.volume_ml,
                "tail_volume_ml": tail_volume_ml,
                "keg_id": str(keg.keg_id),
                "keg_current_volume_ml": keg.current_volume_ml,
            },
            reason="insufficient_keg_volume",
            outcome="rejected_insufficient_keg_volume",
        )

    pending_pour.client_tx_id = pour_data.client_tx_id
    pending_pour.card_uid = pour_data.card_uid
    pending_pour.tap_id = pour_data.tap_id
    pending_pour.visit_id = active_visit.visit_id
    pending_pour.volume_ml = pour_data.volume_ml
    pending_pour.poured_at = func.now()
    pending_pour.amount_charged = amount_to_charge
    pending_pour.price_per_ml_at_pour = price_per_ml
    pending_pour.duration_ms = duration_ms
    pending_pour.guest_id = guest.guest_id
    pending_pour.keg_id = keg.keg_id
    pending_pour.sync_status = "synced"
    pending_pour.synced_at = func.now()
    pending_pour.reconciled_at = None
    pending_pour.short_id = pour_data.short_id
    pending_pour.is_manual_reconcile = False

    guest.balance -= amount_to_charge
    keg.current_volume_ml -= pour_data.volume_ml
    _clear_active_visit_lock(active_visit=active_visit, tap=tap, keg=keg)
    db.flush()
    db.refresh(pending_pour)
    get_pos_adapter().notify_pour(db=db, pour=pending_pour, guest=guest)

    return _result("accepted", "pending_updated_to_synced", "Pour processed successfully.")


def get_pours(db: Session, skip: int = 0, limit: int = 20):
    return (
        db.query(models.Pour)
        .options(
            joinedload(models.Pour.guest),
            joinedload(models.Pour.tap),
            joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
        )
        .order_by(
            func.coalesce(
                models.Pour.synced_at,
                models.Pour.reconciled_at,
                models.Pour.authorized_at,
                models.Pour.poured_at,
                models.Pour.created_at,
            ).desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


FINAL_KPI_SYNC_STATUSES = ("synced", "reconciled")


def _is_sqlite(db: Session) -> bool:
    bind = db.get_bind()
    return bind is not None and bind.dialect.name == "sqlite"


def _start_of_current_day_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_today_summary(db: Session) -> schemas.TodaySummaryResponse:
    generated_at = datetime.now(timezone.utc)

    open_shift = (
        db.query(models.Shift)
        .filter(models.Shift.status == "open")
        .order_by(models.Shift.opened_at.desc())
        .first()
    )

    if open_shift is not None:
        period = "shift"
        window_start = open_shift.opened_at
        window_end = generated_at
        shift_id = open_shift.id
        opened_at = open_shift.opened_at
        closed_at = open_shift.closed_at
        fallback_copy = None
    else:
        period = "day"
        window_start = _start_of_current_day_utc()
        window_end = generated_at
        shift_id = None
        opened_at = None
        closed_at = None
        fallback_copy = "Смена сейчас закрыта, поэтому KPI показаны только за текущий календарный день (UTC)."

    timestamp_column = func.coalesce(
        models.Pour.synced_at,
        models.Pour.reconciled_at,
        models.Pour.poured_at,
        models.Pour.created_at,
    )

    if _is_sqlite(db):
        window_start_text = window_start.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        window_end_text = window_end.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        filters = [
            func.strftime("%Y-%m-%d %H:%M:%S", timestamp_column) >= window_start_text,
            func.strftime("%Y-%m-%d %H:%M:%S", timestamp_column) <= window_end_text,
        ]
    else:
        filters = [timestamp_column >= window_start, timestamp_column <= window_end]

    totals = (
        db.query(
            func.count(func.distinct(models.Pour.visit_id)).label("sessions_count"),
            func.coalesce(func.sum(models.Pour.volume_ml), 0).label("volume_ml"),
            func.coalesce(func.sum(models.Pour.amount_charged), 0).label("revenue"),
            func.coalesce(
                func.sum(case((models.Pour.sync_status == "pending_sync", 1), else_=0)),
                0,
            ).label("pending_sync_count"),
        )
        .filter(*filters)
        .filter(models.Pour.sync_status.in_(FINAL_KPI_SYNC_STATUSES))
        .one()
    )

    pending_sync_count = (
        db.query(func.count(models.Pour.pour_id))
        .filter(*filters)
        .filter(models.Pour.sync_status == "pending_sync")
        .scalar()
    )

    if pending_sync_count:
        pending_copy = f"Есть {int(pending_sync_count)} налив(ов) в ожидании синхронизации, поэтому KPI обновятся после подтверждения backend."
        fallback_copy = f"{fallback_copy} {pending_copy}".strip() if fallback_copy else pending_copy

    return schemas.TodaySummaryResponse(
        period=period,
        summary_complete=pending_sync_count == 0 and open_shift is not None,
        fallback_copy=fallback_copy,
        shift_id=shift_id,
        opened_at=opened_at,
        closed_at=closed_at,
        generated_at=generated_at,
        sessions_count=int(totals.sessions_count or 0),
        volume_ml=int(totals.volume_ml or 0),
        revenue=totals.revenue or 0,
    )


def get_live_feed(db: Session, limit: int = 20):
    pours = (
        db.query(models.Pour)
        .options(
            joinedload(models.Pour.guest),
            joinedload(models.Pour.tap),
            joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
        )
        .filter(models.Pour.sync_status != "pending_sync", models.Pour.volume_ml > 0)
        .order_by(
            func.coalesce(
                models.Pour.synced_at,
                models.Pour.reconciled_at,
                models.Pour.authorized_at,
                models.Pour.poured_at,
                models.Pour.created_at,
            ).desc()
        )
        .limit(limit)
        .all()
    )
    flow_events = controller_crud.get_latest_flow_events(db, limit=limit)

    items = []
    terminal_short_ids = {pour.short_id for pour in pours if pour.short_id}
    for pour in pours:
        timestamp = pour.ended_at or pour.poured_at or pour.authorized_at or pour.created_at
        items.append(
            {
                "item_id": str(pour.pour_id),
                "item_type": "pour",
                "status": pour.sync_status,
                "tap_id": pour.tap_id,
                "tap_name": pour.tap.display_name if pour.tap else None,
                "timestamp": timestamp,
                "started_at": pour.started_at,
                "ended_at": pour.ended_at,
                "duration_ms": pour.duration_ms,
                "volume_ml": pour.volume_ml,
                "amount_charged": pour.amount_charged,
                "short_id": pour.short_id,
                "guest": {
                    "guest_id": pour.guest.guest_id,
                    "last_name": pour.guest.last_name,
                    "first_name": pour.guest.first_name,
                }
                if pour.guest
                else None,
                "beverage_name": pour.beverage.name if pour.beverage else None,
                "card_uid": pour.card_uid,
                "card_present": True,
                "session_state": "authorized_session",
                "valve_open": False,
                "reason": None,
                "event_status": None,
            }
        )

    for flow_event in flow_events:
        if (
            flow_event.get("session_state") == "authorized_session"
            and flow_event.get("short_id")
            and flow_event.get("short_id") in terminal_short_ids
        ):
            continue
        items.append(flow_event)
    items.sort(key=lambda item: item["timestamp"], reverse=True)
    return items[:limit]
