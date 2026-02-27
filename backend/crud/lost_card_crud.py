from datetime import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

import models


def _normalize_card_uid(card_uid: str) -> str:
    return card_uid.strip().lower()


def get_lost_card_by_uid(db: Session, card_uid: str):
    normalized_uid = _normalize_card_uid(card_uid)
    return (
        db.query(models.LostCard)
        .filter(func.lower(models.LostCard.card_uid) == normalized_uid)
        .first()
    )


def is_lost_card(db: Session, card_uid: str) -> bool:
    return get_lost_card_by_uid(db=db, card_uid=card_uid) is not None


def create_lost_card_idempotent(
    db: Session,
    *,
    card_uid: str,
    reported_by: str | None = None,
    reason: str | None = None,
    comment: str | None = None,
    visit_id: uuid.UUID | None = None,
    guest_id: uuid.UUID | None = None,
):
    normalized_uid = _normalize_card_uid(card_uid)
    existing = get_lost_card_by_uid(db=db, card_uid=normalized_uid)
    if existing:
        changed = False
        if visit_id and not existing.visit_id:
            existing.visit_id = visit_id
            changed = True
        if guest_id and not existing.guest_id:
            existing.guest_id = guest_id
            changed = True
        if reported_by and not existing.reported_by:
            existing.reported_by = reported_by
            changed = True
        if reason and not existing.reason:
            existing.reason = reason
            changed = True
        if comment and not existing.comment:
            existing.comment = comment
            changed = True
        if changed:
            db.commit()
            db.refresh(existing)
        return existing, False

    lost_card = models.LostCard(
        card_uid=normalized_uid,
        reported_by=reported_by,
        reason=reason,
        comment=comment,
        visit_id=visit_id,
        guest_id=guest_id,
    )
    db.add(lost_card)
    db.commit()
    db.refresh(lost_card)
    return lost_card, True


def list_lost_cards(
    db: Session,
    *,
    card_uid: str | None = None,
    reported_from: datetime | None = None,
    reported_to: datetime | None = None,
):
    query = db.query(models.LostCard)
    if card_uid:
        pattern = f"%{card_uid.strip().lower()}%"
        query = query.filter(func.lower(models.LostCard.card_uid).like(pattern))
    if reported_from:
        query = query.filter(models.LostCard.reported_at >= reported_from)
    if reported_to:
        query = query.filter(models.LostCard.reported_at <= reported_to)

    return query.order_by(models.LostCard.reported_at.desc()).all()


def restore_lost_card(db: Session, card_uid: str):
    lost_card = get_lost_card_by_uid(db=db, card_uid=card_uid)
    if not lost_card:
        return None
    restored_uid = lost_card.card_uid
    db.delete(lost_card)
    db.commit()
    return restored_uid
