from datetime import datetime, timezone, date
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models


def _is_adult(date_of_birth: date) -> bool:
    today = date.today()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years >= 18


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


def get_active_visit_by_guest_id(db: Session, guest_id: uuid.UUID):
    return db.query(models.Visit).filter(
        models.Visit.guest_id == guest_id,
        models.Visit.status == "active",
    ).first()


def get_active_visit_by_card_uid(db: Session, card_uid: str):
    return db.query(models.Visit).filter(
        models.Visit.card_uid == card_uid,
        models.Visit.status == "active",
    ).first()


def search_active_visit_by_guest_query(db: Session, query: str):
    normalized = query.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Query must not be empty")

    like_query = f"%{normalized.lower()}%"

    return db.query(models.Visit).join(models.Guest, models.Visit.guest_id == models.Guest.guest_id).filter(
        models.Visit.status == "active",
        or_(
            models.Guest.phone_number.ilike(like_query),
            models.Guest.last_name.ilike(like_query),
            models.Guest.first_name.ilike(like_query),
            models.Guest.patronymic.ilike(like_query),
        ),
    ).order_by(models.Visit.opened_at.desc()).first()


def get_visit(db: Session, visit_id: uuid.UUID):
    return db.query(models.Visit).filter(models.Visit.visit_id == visit_id).first()


def get_active_visits_list(db: Session):
    visits = db.query(models.Visit).join(models.Guest, models.Visit.guest_id == models.Guest.guest_id).filter(
        models.Visit.status == "active"
    ).order_by(models.Visit.opened_at.desc()).all()

    result = []
    for visit in visits:
        guest = visit.guest
        full_name = " ".join([part for part in [guest.last_name, guest.first_name, guest.patronymic] if part]) if guest else "—"
        result.append({
            "visit_id": visit.visit_id,
            "guest_id": visit.guest_id,
            "guest_full_name": full_name,
            "phone_number": guest.phone_number if guest else "",
            "balance": guest.balance if guest else 0,
            "status": visit.status,
            "card_uid": visit.card_uid,
            "active_tap_id": visit.active_tap_id,
            "lock_set_at": visit.lock_set_at,
            "opened_at": visit.opened_at,
        })
    return result


def open_visit(db: Session, guest_id: uuid.UUID, card_uid: str | None = None):
    guest = db.query(models.Guest).filter(models.Guest.guest_id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    if not _is_adult(guest.date_of_birth):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Guest must be 18+ to open visit")

    existing_guest_visit = get_active_visit_by_guest_id(db=db, guest_id=guest_id)
    if existing_guest_visit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Guest already has an active visit", "visit_id": str(existing_guest_visit.visit_id)},
        )

    card = None
    if card_uid is not None:
        card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        if card.guest_id != guest_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is not assigned to this guest")

        existing_card_visit = get_active_visit_by_card_uid(db=db, card_uid=card_uid)
        if existing_card_visit:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")

    try:
        visit = models.Visit(
            guest_id=guest_id,
            card_uid=card_uid,
            status="active",
            active_tap_id=None,
            card_returned=True,
        )
        db.add(visit)

        if card is not None:
            card.status = "active"

        db.commit()
        db.refresh(visit)
        return visit
    except IntegrityError as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_visits_one_active_per_guest" in message:
            detail = "Guest already has an active visit"
        elif "uq_visits_one_active_per_card" in message:
            detail = "Card already used by another active visit"
        else:
            detail = "Visit invariant violation"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def authorize_pour_lock(db: Session, card_uid: str, tap_id: int, actor_id: str):
    active_visit = get_active_visit_by_card_uid(db=db, card_uid=card_uid)
    if not active_visit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"No active visit for Card {card_uid}.")

    lock_attempt = db.execute(
        update(models.Visit)
        .where(
            models.Visit.visit_id == active_visit.visit_id,
            models.Visit.status == "active",
            or_(models.Visit.active_tap_id.is_(None), models.Visit.active_tap_id == tap_id),
        )
        .values(active_tap_id=tap_id, lock_set_at=datetime.now(timezone.utc))
    )

    if lock_attempt.rowcount == 0:
        current = get_visit(db, active_visit.visit_id)
        current_tap_id = current.active_tap_id if current else None
        _add_audit_log(
            db,
            actor_id=actor_id,
            action="card_in_use_on_other_tap",
            target_entity="Visit",
            target_id=str(active_visit.visit_id),
            details={
                "card_uid": card_uid,
                "requested_tap_id": tap_id,
                "active_tap_id": current_tap_id,
                "event": "authorize_conflict",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card already in use on Tap {current_tap_id}",
        )

    tap = db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()
    if tap and tap.status == "active":
        tap.status = "processing_sync"

    db.commit()
    db.refresh(active_visit)
    return active_visit


def force_unlock_visit(db: Session, visit_id: uuid.UUID, reason: str, comment: str | None, actor_id: str):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can be force-unlocked")

    previous_tap_id = visit.active_tap_id
    visit.active_tap_id = None
    visit.lock_set_at = None

    if previous_tap_id is not None:
        tap = db.query(models.Tap).filter(models.Tap.tap_id == previous_tap_id).first()
        if tap and tap.status == "processing_sync":
            tap.status = "active"

    _add_audit_log(
        db,
        actor_id=actor_id,
        action="visit_force_unlock",
        target_entity="Visit",
        target_id=str(visit.visit_id),
        details={
            "card_uid": visit.card_uid,
            "previous_tap_id": previous_tap_id,
            "reason": reason,
            "comment": comment,
        },
    )

    db.commit()
    db.refresh(visit)
    return visit


def close_visit(db: Session, visit_id: uuid.UUID, closed_reason: str, card_returned: bool):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit is already closed")

    visit.status = "closed"
    visit.closed_reason = closed_reason
    visit.closed_at = datetime.now(timezone.utc)
    visit.card_returned = card_returned
    previous_tap_id = visit.active_tap_id
    visit.active_tap_id = None
    visit.lock_set_at = None

    if previous_tap_id is not None:
        tap = db.query(models.Tap).filter(models.Tap.tap_id == previous_tap_id).first()
        if tap and tap.status == "processing_sync":
            tap.status = "active"

    if visit.card_uid is not None:
        card = db.query(models.Card).filter(models.Card.card_uid == visit.card_uid).first()
        if card:
            card.status = "inactive"

    db.commit()
    db.refresh(visit)
    return visit


def assign_card_to_active_visit(db: Session, visit_id: uuid.UUID, card_uid: str):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can be updated")
    if visit.card_uid is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit already has a card")

    existing_card_visit = get_active_visit_by_card_uid(db=db, card_uid=card_uid)
    if existing_card_visit and existing_card_visit.visit_id != visit.visit_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")

    card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if card:
        if card.guest_id and card.guest_id != visit.guest_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is assigned to another guest")
        if card.guest_id is None:
            card.guest_id = visit.guest_id
    else:
        card = models.Card(card_uid=card_uid, guest_id=visit.guest_id, status="inactive")
        db.add(card)

    visit.card_uid = card_uid
    card.status = "active"

    try:
        db.commit()
        db.refresh(visit)
        return visit
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")


def reconcile_pour(
    db: Session,
    *,
    visit_id: uuid.UUID,
    tap_id: int,
    short_id: str,
    volume_ml: int,
    amount,
    reason: str,
    comment: str | None,
    actor_id: str,
):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    existing = (
        db.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.short_id == short_id,
            models.Pour.is_manual_reconcile.is_(True),
        )
        .first()
    )
    if existing:
        if visit.active_tap_id == tap_id:
            visit.active_tap_id = None
            visit.lock_set_at = None
            tap = db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()
            if tap and tap.status == "processing_sync":
                tap.status = "active"
        db.commit()
        db.refresh(visit)
        return visit

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active visit can be reconciled")
    if visit.active_tap_id != tap_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Visit is not locked on Tap {tap_id}")
    if not visit.card_uid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit has no card assigned")

    tap = (
        db.query(models.Tap)
        .filter(models.Tap.tap_id == tap_id)
        .first()
    )
    if not tap or not tap.keg_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tap is not configured with keg")

    guest = db.query(models.Guest).filter(models.Guest.guest_id == visit.guest_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    if guest.balance < amount:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient guest balance for manual reconcile")

    keg = db.query(models.Keg).filter(models.Keg.keg_id == tap.keg_id).first()
    if not keg:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keg not found")
    if keg.current_volume_ml < volume_ml:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient keg volume for manual reconcile")

    manual_client_tx_id = f"manual-reconcile:{visit_id}:{short_id}"
    price_per_ml = (Decimal(amount) / Decimal(volume_ml)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    db.add(
        models.Pour(
            client_tx_id=manual_client_tx_id,
            card_uid=visit.card_uid,
            tap_id=tap_id,
            visit_id=visit_id,
            volume_ml=volume_ml,
            poured_at=datetime.now(timezone.utc),
            amount_charged=amount,
            price_per_ml_at_pour=price_per_ml,
            guest_id=visit.guest_id,
            keg_id=tap.keg_id,
            sync_status="reconciled",
            short_id=short_id,
            is_manual_reconcile=True,
        )
    )

    guest.balance -= amount
    keg.current_volume_ml -= volume_ml
    visit.active_tap_id = None
    visit.lock_set_at = None
    if tap.status == "processing_sync":
        tap.status = "active"

    _add_audit_log(
        db,
        actor_id=actor_id,
        action="reconcile_done",
        target_entity="Visit",
        target_id=str(visit.visit_id),
        details={
            "tap_id": tap_id,
            "short_id": short_id,
            "volume_ml": volume_ml,
            "amount": str(amount),
            "reason": reason,
            "comment": comment,
        },
    )

    db.commit()
    db.refresh(visit)
    return visit
