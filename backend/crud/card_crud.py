# backend/crud/card_crud.py
from decimal import Decimal, ROUND_HALF_UP
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import lost_card_crud


def create_card(db: Session, card: schemas.CardCreate):
    db_card_by_uid = db.query(models.Card).filter(models.Card.card_uid == card.card_uid).first()
    if db_card_by_uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card with UID {card.card_uid} already registered.",
        )

    db_card = models.Card(card_uid=card.card_uid, status="inactive")
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def get_card_by_uid(db: Session, uid: str):
    return db.query(models.Card).filter(models.Card.card_uid == uid).first()


def get_cards(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Card)
        .options(joinedload(models.Card.guest))
        .order_by(models.Card.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_card_status(db: Session, card_uid: str, new_status: str):
    db_card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if not db_card:
        return None

    db_card.status = new_status
    db.commit()
    db.refresh(db_card)
    return db_card


def assign_card_to_guest(db: Session, db_card: models.Card, guest_id: uuid.UUID):
    db_card.guest_id = guest_id
    # Card is operationally activated by opening a Visit (M2).
    db_card.status = "inactive"
    db.commit()
    db.refresh(db_card)
    return db_card


def create_and_assign_card(db: Session, card: schemas.CardCreate, guest_id: uuid.UUID):
    db_card = models.Card(
        card_uid=card.card_uid,
        guest_id=guest_id,
        # Card is operationally activated by opening a Visit (M2).
        status="inactive",
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def _normalize_card_uid(card_uid: str) -> str:
    return card_uid.strip().lower()


def _get_card_by_uid_case_insensitive(db: Session, card_uid: str):
    normalized_uid = _normalize_card_uid(card_uid)
    if not normalized_uid:
        return None
    return (
        db.query(models.Card)
        .filter(func.lower(models.Card.card_uid) == normalized_uid)
        .first()
    )


def _get_active_visit_by_card_uid_case_insensitive(db: Session, card_uid: str):
    normalized_uid = _normalize_card_uid(card_uid)
    if not normalized_uid:
        return None
    return (
        db.query(models.Visit)
        .filter(
            models.Visit.status == "active",
            func.lower(models.Visit.card_uid) == normalized_uid,
        )
        .first()
    )


def _guest_full_name(guest: models.Guest | None) -> str:
    if not guest:
        return "-"
    return " ".join([part for part in [guest.last_name, guest.first_name, guest.patronymic] if part])


def _guest_balance_cents(balance) -> int:
    amount = Decimal(str(balance or 0))
    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def _resolve_guest_for_card(
    db: Session,
    *,
    card: models.Card | None,
    active_visit: models.Visit | None,
    lost_card: models.LostCard | None,
):
    if card and card.guest_id:
        guest = db.query(models.Guest).filter(models.Guest.guest_id == card.guest_id).first()
        if guest:
            return guest

    if active_visit and active_visit.guest_id:
        guest = active_visit.guest
        if guest:
            return guest
        guest = db.query(models.Guest).filter(models.Guest.guest_id == active_visit.guest_id).first()
        if guest:
            return guest

    if lost_card:
        if lost_card.guest_id:
            guest = db.query(models.Guest).filter(models.Guest.guest_id == lost_card.guest_id).first()
            if guest:
                return guest
        if lost_card.visit_id:
            lost_visit = db.query(models.Visit).filter(models.Visit.visit_id == lost_card.visit_id).first()
            if lost_visit and lost_visit.guest_id:
                guest = lost_visit.guest
                if guest:
                    return guest
                guest = db.query(models.Guest).filter(models.Guest.guest_id == lost_visit.guest_id).first()
                if guest:
                    return guest

    return None


def resolve_card(db: Session, card_uid: str):
    requested_uid = card_uid.strip()
    lost_card = lost_card_crud.get_lost_card_by_uid(db=db, card_uid=requested_uid)
    card = _get_card_by_uid_case_insensitive(db=db, card_uid=requested_uid)
    active_visit = _get_active_visit_by_card_uid_case_insensitive(db=db, card_uid=requested_uid)
    guest = _resolve_guest_for_card(db=db, card=card, active_visit=active_visit, lost_card=lost_card)

    if lost_card:
        recommended_action = "lost_restore"
    elif active_visit:
        recommended_action = "open_active_visit"
    elif guest:
        recommended_action = "open_new_visit"
    elif card:
        recommended_action = "bind_card"
    else:
        recommended_action = "unknown"

    lost_card_payload = None
    if lost_card:
        lost_card_payload = {
            "reported_at": lost_card.reported_at,
            "comment": lost_card.comment,
            "visit_id": lost_card.visit_id,
            "reported_by": lost_card.reported_by,
            "reason": lost_card.reason,
            "guest_id": lost_card.guest_id,
        }

    active_visit_payload = None
    if active_visit:
        guest_for_visit = active_visit.guest or guest
        active_visit_payload = {
            "visit_id": active_visit.visit_id,
            "guest_id": active_visit.guest_id,
            "guest_full_name": _guest_full_name(guest_for_visit),
            "phone_number": guest_for_visit.phone_number if guest_for_visit else "",
            "status": active_visit.status,
            "card_uid": active_visit.card_uid,
            "active_tap_id": active_visit.active_tap_id,
            "opened_at": active_visit.opened_at,
        }

    guest_payload = None
    if guest:
        guest_payload = {
            "guest_id": guest.guest_id,
            "full_name": _guest_full_name(guest),
            "phone_number": guest.phone_number,
            "balance_cents": _guest_balance_cents(guest.balance),
        }

    card_payload = None
    if card:
        card_payload = {
            "uid": card.card_uid,
            "status": card.status,
            "guest_id": card.guest_id,
        }

    return {
        "card_uid": card.card_uid if card else requested_uid,
        "is_lost": lost_card is not None,
        "lost_card": lost_card_payload,
        "active_visit": active_visit_payload,
        "guest": guest_payload,
        "card": card_payload,
        "recommended_action": recommended_action,
    }
