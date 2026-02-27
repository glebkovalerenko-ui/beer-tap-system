from decimal import Decimal, ROUND_HALF_UP
import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import visit_crud


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

    price_per_ml = beverage.sell_price_per_liter / Decimal(1000)
    amount_to_charge = (Decimal(pour_data.volume_ml) * price_per_ml).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if guest.balance < amount_to_charge:
        return _result("rejected", "rejected_insufficient_funds", f"Insufficient funds for Guest {guest.guest_id}.")

    if keg.current_volume_ml < pour_data.volume_ml:
        return _result("rejected", "rejected_insufficient_keg_volume", f"Insufficient volume in Keg {keg.keg_id}.")

    pending_pour = get_pending_pour_for_visit_tap(db=db, visit_id=active_visit.visit_id, tap_id=pour_data.tap_id)
    result_outcome = "pending_updated_to_synced"
    if pending_pour:
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
    else:
        result_outcome = "synced_without_pending"
        _create_pour_record(
            db=db,
            pour_data=pour_data,
            duration_ms=duration_ms,
            guest_id=guest.guest_id,
            visit_id=active_visit.visit_id,
            keg_id=keg.keg_id,
            amount_charged=amount_to_charge,
            price_per_ml=price_per_ml,
            sync_status="synced",
        )

    guest.balance -= amount_to_charge
    keg.current_volume_ml -= pour_data.volume_ml
    active_visit.active_tap_id = None
    active_visit.lock_set_at = None

    if keg.current_volume_ml <= 0:
        keg.status = "empty"
        tap.status = "empty"
        keg.finished_at = func.now()
    else:
        tap.status = "active"

    return _result("accepted", result_outcome, "Pour processed successfully.")


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
