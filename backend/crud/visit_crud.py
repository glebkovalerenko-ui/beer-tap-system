from datetime import datetime, timezone, date
import json
import uuid

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


def open_visit(db: Session, guest_id: uuid.UUID, card_uid: str):
    guest = db.query(models.Guest).filter(models.Guest.guest_id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    if not _is_adult(guest.date_of_birth):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Guest must be 18+ to open visit")

    card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    if card.guest_id != guest_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is not assigned to this guest")

    existing_guest_visit = get_active_visit_by_guest_id(db=db, guest_id=guest_id)
    if existing_guest_visit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest already has an active visit")

    existing_card_visit = get_active_visit_by_card_uid(db=db, card_uid=card_uid)
    if existing_card_visit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already used by another active visit")

    try:
        visit = models.Visit(
            guest_id=guest_id,
            card_uid=card_uid,
            status="active",
            card_returned=True,
        )
        db.add(visit)

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
        .values(active_tap_id=tap_id)
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
    visit.active_tap_id = None

    card = db.query(models.Card).filter(models.Card.card_uid == visit.card_uid).first()
    if card:
        card.status = "inactive"

    db.commit()
    db.refresh(visit)
    return visit
