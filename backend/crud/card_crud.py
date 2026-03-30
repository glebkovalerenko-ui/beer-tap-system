# backend/crud/card_crud.py
from decimal import Decimal, ROUND_HALF_UP
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import lost_card_crud


CARD_STATUS_AVAILABLE = "available"
CARD_STATUS_ASSIGNED = "assigned_to_visit"
CARD_STATUS_RETURNED = "returned_to_pool"
CARD_STATUS_LOST = "lost"
CARD_STATUS_RETIRED = "retired"

LOOKUP_ACTIVE_VISIT = "active_visit"
LOOKUP_ACTIVE_BLOCKED_LOST = "active_blocked_lost_card"
LOOKUP_AVAILABLE = "available_pool_card"
LOOKUP_RETURNED = "returned_to_pool_card"
LOOKUP_LOST = "lost_card"
LOOKUP_RETIRED = "retired_card"
LOOKUP_UNKNOWN = "unknown_card"


def normalize_card_uid(card_uid: str) -> str:
    normalized = str(card_uid or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Card UID must not be empty")
    return normalized


def _guest_full_name(guest: models.Guest | None) -> str:
    if not guest:
        return "-"
    return " ".join([part for part in [guest.last_name, guest.first_name, guest.patronymic] if part])


def _guest_balance_cents(balance) -> int:
    amount = Decimal(str(balance or 0))
    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def create_card(db: Session, card: schemas.CardCreate):
    normalized_uid = normalize_card_uid(card.card_uid)
    db_card_by_uid = _get_card_by_uid_case_insensitive(db, normalized_uid)
    if db_card_by_uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card with UID {normalized_uid} already registered.",
        )

    db_card = models.Card(card_uid=normalized_uid, status=CARD_STATUS_AVAILABLE)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def get_card_by_uid(db: Session, uid: str):
    normalized_uid = normalize_card_uid(uid)
    return _get_card_by_uid_case_insensitive(db, normalized_uid)


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
    db_card = get_card_by_uid(db, card_uid)
    if not db_card:
        return None

    db_card.status = str(new_status).strip()
    db.commit()
    db.refresh(db_card)
    return db_card


def assign_card_to_guest(db: Session, db_card: models.Card, guest_id: uuid.UUID):
    # Legacy compatibility path only. Do not change operational card ownership.
    db_card.guest_id = guest_id
    if db_card.status in {"inactive", "active"}:
        db_card.status = CARD_STATUS_AVAILABLE
    db.commit()
    db.refresh(db_card)
    return db_card


def create_and_assign_card(db: Session, card: schemas.CardCreate, guest_id: uuid.UUID):
    normalized_uid = normalize_card_uid(card.card_uid)
    db_card = models.Card(
        card_uid=normalized_uid,
        guest_id=guest_id,
        status=CARD_STATUS_AVAILABLE,
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def _get_card_by_uid_case_insensitive(db: Session, card_uid: str):
    normalized_uid = normalize_card_uid(card_uid)
    return (
        db.query(models.Card)
        .filter(func.lower(models.Card.card_uid) == normalized_uid)
        .first()
    )


def _get_active_visit_by_card_uid_case_insensitive(db: Session, card_uid: str):
    normalized_uid = normalize_card_uid(card_uid)
    return (
        db.query(models.Visit)
        .options(joinedload(models.Visit.guest))
        .filter(
            models.Visit.status == "active",
            func.lower(models.Visit.card_uid) == normalized_uid,
        )
        .first()
    )


def _resolve_guest_for_card(
    db: Session,
    *,
    card: models.Card | None,
    active_visit: models.Visit | None,
    lost_card: models.LostCard | None,
):
    if active_visit and active_visit.guest_id:
        guest = active_visit.guest
        if guest:
            return guest
        guest = db.query(models.Guest).filter(models.Guest.guest_id == active_visit.guest_id).first()
        if guest:
            return guest

    if lost_card:
        if lost_card.visit_id:
            lost_visit = (
                db.query(models.Visit)
                .options(joinedload(models.Visit.guest))
                .filter(models.Visit.visit_id == lost_card.visit_id)
                .first()
            )
            if lost_visit and lost_visit.guest:
                return lost_visit.guest
            if lost_visit and lost_visit.guest_id:
                guest = db.query(models.Guest).filter(models.Guest.guest_id == lost_visit.guest_id).first()
                if guest:
                    return guest
        if lost_card.guest_id:
            guest = db.query(models.Guest).filter(models.Guest.guest_id == lost_card.guest_id).first()
            if guest:
                return guest

    return None


def _lookup_outcome_for(card: models.Card | None, active_visit: models.Visit | None, lost_card: models.LostCard | None) -> str:
    if active_visit and active_visit.operational_status == LOOKUP_ACTIVE_BLOCKED_LOST:
        return LOOKUP_ACTIVE_BLOCKED_LOST
    if active_visit:
        return LOOKUP_ACTIVE_VISIT
    if lost_card or (card and card.status == CARD_STATUS_LOST):
        return LOOKUP_LOST
    if card and card.status == CARD_STATUS_AVAILABLE:
        return LOOKUP_AVAILABLE
    if card and card.status == CARD_STATUS_RETURNED:
        return LOOKUP_RETURNED
    if card and card.status == CARD_STATUS_RETIRED:
        return LOOKUP_RETIRED
    return LOOKUP_UNKNOWN


def _allowed_actions_for(outcome: str) -> tuple[str, list[str]]:
    mapping = {
        LOOKUP_ACTIVE_VISIT: ("open_visit_workspace", ["open_visit_workspace", "mark_lost", "normal_close_scan"]),
        LOOKUP_ACTIVE_BLOCKED_LOST: ("open_visit_workspace", ["open_visit_workspace", "reissue_card_for_visit", "service_close_missing_card"]),
        LOOKUP_AVAILABLE: ("issue_on_open_visit", ["issue_on_open_visit"]),
        LOOKUP_RETURNED: ("issue_on_open_visit", ["issue_on_open_visit"]),
        LOOKUP_LOST: ("open_related_visit_if_any", ["open_related_visit_if_any"]),
        LOOKUP_RETIRED: ("inventory_review", ["inventory_review"]),
        LOOKUP_UNKNOWN: ("register_into_pool_if_inventory_flow_allows", ["register_into_pool_if_inventory_flow_allows"]),
    }
    return mapping[outcome]


def resolve_card(db: Session, card_uid: str):
    requested_uid = normalize_card_uid(card_uid)
    lost_card = lost_card_crud.get_lost_card_by_uid(db=db, card_uid=requested_uid)
    card = _get_card_by_uid_case_insensitive(db=db, card_uid=requested_uid)
    active_visit = _get_active_visit_by_card_uid_case_insensitive(db=db, card_uid=requested_uid)
    guest = _resolve_guest_for_card(db=db, card=card, active_visit=active_visit, lost_card=lost_card)
    lookup_outcome = _lookup_outcome_for(card=card, active_visit=active_visit, lost_card=lost_card)
    recommended_action, allowed_next_actions = _allowed_actions_for(lookup_outcome)

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
            "operational_status": active_visit.operational_status,
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
            # Legacy guest binding must not leak back as operator-facing operational truth.
            "guest_id": None,
        }

    return {
        "card_uid": card.card_uid if card else requested_uid,
        "is_lost": lookup_outcome in {LOOKUP_LOST, LOOKUP_ACTIVE_BLOCKED_LOST},
        "lookup_outcome": lookup_outcome,
        "lost_card": lost_card_payload,
        "active_visit": active_visit_payload,
        "guest": guest_payload,
        "card": card_payload,
        "recommended_action": recommended_action,
        "allowed_next_actions": allowed_next_actions,
    }
