# backend/crud/pour_crud.py
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
import json
import models
import schemas
from crud import visit_crud
import uuid


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


def get_pour_by_client_tx_id(db: Session, client_tx_id: str):
    """Проверяет, существует ли уже транзакция с таким ID от клиента."""
    return db.query(models.Pour).filter(models.Pour.client_tx_id == client_tx_id).first()


def _create_pour_record(
    db: Session,
    pour_data: schemas.PourData,
    guest_id: uuid.UUID,
    visit_id: uuid.UUID,
    keg_id: uuid.UUID,
    amount_charged: Decimal,
    price_per_ml: Decimal,
):
    db_pour = models.Pour(
        client_tx_id=pour_data.client_tx_id,
        card_uid=pour_data.card_uid,
        tap_id=pour_data.tap_id,
        visit_id=visit_id,
        volume_ml=pour_data.volume_ml,
        poured_at=pour_data.start_ts,
        amount_charged=amount_charged,
        price_per_ml_at_pour=price_per_ml,
        guest_id=guest_id,
        keg_id=keg_id,
    )
    db.add(db_pour)
    return db_pour


def process_pour(db: Session, pour_data: schemas.PourData):
    card = db.query(models.Card).options(joinedload(models.Card.guest)).filter(models.Card.card_uid == pour_data.card_uid).first()
    tap = db.query(models.Tap).options(joinedload(models.Tap.keg).joinedload(models.Keg.beverage)).filter(models.Tap.tap_id == pour_data.tap_id).first()

    if not (card and card.guest and tap and tap.keg and tap.keg.beverage):
        return {
            "status": "rejected",
            "reason": f"Invalid data: Card UID {pour_data.card_uid} or Tap ID {pour_data.tap_id} not found or not fully configured.",
        }

    guest = card.guest
    keg = tap.keg
    beverage = keg.beverage

    if not guest.is_active or card.status != "active":
        return {"status": "rejected", "reason": f"Guest {guest.guest_id} or Card {card.card_uid} is not active."}

    active_visit = visit_crud.get_active_visit_by_card_uid(db=db, card_uid=card.card_uid)
    if not active_visit:
        return {"status": "rejected", "reason": f"No active visit for Card {card.card_uid}."}

    if active_visit.active_tap_id is None:
        _add_audit_log(
            db,
            actor_id="internal_rpi",
            action="late_or_out_of_order_sync",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": card.card_uid,
                "tap_id": pour_data.tap_id,
                "client_tx_id": pour_data.client_tx_id,
                "event": "sync_without_active_lock",
            },
        )
        return {
            "status": "rejected",
            "reason": "Late/out-of-order sync: active tap lock is not present",
        }

    if active_visit.active_tap_id != pour_data.tap_id:
        _add_audit_log(
            db,
            actor_id="internal_rpi",
            action="card_in_use_on_other_tap",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": card.card_uid,
                "requested_tap_id": pour_data.tap_id,
                "active_tap_id": active_visit.active_tap_id,
                "event": "sync_conflict",
                "client_tx_id": pour_data.client_tx_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card already in use on Tap {active_visit.active_tap_id}",
        )

    if tap.status != "active" or keg.status != "in_use":
        return {"status": "rejected", "reason": f"Tap {tap.tap_id} or Keg {keg.keg_id} is not in 'active'/'in_use' state."}

    price_per_ml = beverage.sell_price_per_liter / Decimal(1000)
    amount_to_charge = (Decimal(pour_data.volume_ml) * price_per_ml).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if guest.balance < amount_to_charge:
        return {"status": "rejected", "reason": f"Insufficient funds for Guest {guest.guest_id}."}

    if keg.current_volume_ml < pour_data.volume_ml:
        return {"status": "rejected", "reason": f"Insufficient volume in Keg {keg.keg_id}."}

    try:
        _create_pour_record(db, pour_data, guest.guest_id, active_visit.visit_id, keg.keg_id, amount_to_charge, price_per_ml)
        guest.balance -= amount_to_charge
        keg.current_volume_ml -= pour_data.volume_ml
        active_visit.active_tap_id = None

        if keg.current_volume_ml <= 0:
            keg.status = "empty"
            tap.status = "empty"
            keg.finished_at = pour_data.end_ts

        return {"status": "accepted", "reason": "Pour processed successfully."}

    except Exception as e:
        return {"status": "rejected", "reason": f"Internal server error: {str(e)}"}


def get_pours(db: Session, skip: int = 0, limit: int = 20):
    return db.query(models.Pour).options(
        joinedload(models.Pour.guest),
        joinedload(models.Pour.tap),
        joinedload(models.Pour.keg).joinedload(models.Keg.beverage),
    ).order_by(models.Pour.poured_at.desc()).offset(skip).limit(limit).all()
