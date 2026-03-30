from datetime import date
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import card_crud, visit_crud


def get_guest(db: Session, guest_id: uuid.UUID):
    return (
        db.query(models.Guest)
        .options(joinedload(models.Guest.cards))
        .filter(models.Guest.guest_id == guest_id)
        .first()
    )


def get_guests(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Guest)
        .options(joinedload(models.Guest.cards))
        .order_by(models.Guest.last_name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_guest(db: Session, guest: schemas.GuestCreate):
    db_guest_by_doc = db.query(models.Guest).filter(models.Guest.id_document == guest.id_document).first()
    if db_guest_by_doc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest with this ID document already registered")

    db_guest_by_phone = db.query(models.Guest).filter(models.Guest.phone_number == guest.phone_number).first()
    if db_guest_by_phone:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guest with this phone number already registered")

    db_guest = models.Guest(**guest.model_dump())
    db.add(db_guest)
    db.commit()
    db.refresh(db_guest)
    return db_guest


def update_guest(db: Session, guest_id: uuid.UUID, guest_update: schemas.GuestUpdate) -> Optional[models.Guest]:
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        return None

    update_data = guest_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_guest, key, value)

    db.commit()
    db.refresh(db_guest)
    return db_guest


def assign_card_to_guest(db: Session, guest_id: uuid.UUID, uid: str):
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    db_card = card_crud.get_card_by_uid(db, uid=uid)
    if not db_card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Card with UID {uid} not found. Register it first.")

    if db_card.guest_id is not None:
        if db_card.guest_id == guest_id:
            return db_guest
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is already assigned to another guest")

    db_card.guest_id = guest_id
    if db_card.status in {"inactive", "active"}:
        db_card.status = card_crud.CARD_STATUS_AVAILABLE
    db.commit()
    db.refresh(db_guest)
    return db_guest


def unassign_card_from_guest(db: Session, guest_id: uuid.UUID, card_uid: str):
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    db_card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if not db_card or db_card.guest_id != guest_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or not assigned to this guest")

    active_visit = visit_crud.get_active_visit_by_card_uid(db=db, card_uid=card_uid)
    if active_visit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot unassign card during active visit")

    db_card.guest_id = None
    if db_card.status not in {card_crud.CARD_STATUS_ASSIGNED, card_crud.CARD_STATUS_LOST, card_crud.CARD_STATUS_RETIRED}:
        db_card.status = card_crud.CARD_STATUS_AVAILABLE
    db.commit()
    db.refresh(db_guest)
    return db_guest


def get_guest_history(
    db: Session,
    guest_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    history_items = []

    transactions_query = db.query(models.Transaction).filter(models.Transaction.guest_id == guest_id)
    if start_date:
        transactions_query = transactions_query.filter(models.Transaction.created_at >= start_date)
    if end_date:
        transactions_query = transactions_query.filter(models.Transaction.created_at <= end_date)

    for tx in transactions_query.all():
        details = f"Возврат: {tx.payment_method}" if tx.type == "refund" else f"Пополнение: {tx.payment_method}"
        history_items.append(
            schemas.HistoryItem(
                timestamp=tx.created_at,
                type=tx.type,
                amount=tx.amount,
                details=details,
            )
        )

    pours_query = (
        db.query(models.Pour)
        .filter(models.Pour.guest_id == guest_id)
        .options(joinedload(models.Pour.keg).joinedload(models.Keg.beverage))
    )
    if start_date:
        pours_query = pours_query.filter(models.Pour.poured_at >= start_date)
    if end_date:
        pours_query = pours_query.filter(models.Pour.poured_at <= end_date)

    for pour in pours_query.all():
        beverage_name = pour.keg.beverage.name if pour.keg and pour.keg.beverage else "Unknown Beverage"
        history_items.append(
            schemas.HistoryItem(
                timestamp=pour.poured_at,
                type="pour",
                amount=-pour.amount_charged,
                details=f"Налив: {beverage_name} {pour.volume_ml} мл",
            )
        )

    visit_ids = [
        visit_id
        for (visit_id,) in db.query(models.Visit.visit_id).filter(models.Visit.guest_id == guest_id).all()
    ]
    if visit_ids:
        audit_logs = (
            db.query(models.AuditLog)
            .filter(
                models.AuditLog.target_entity == "Visit",
                models.AuditLog.target_id.in_([str(visit_id) for visit_id in visit_ids]),
                models.AuditLog.action.in_([
                    "visit_card_issue",
                    "visit_card_return",
                    "visit_card_lost",
                    "visit_card_reissue",
                    "visit_service_close",
                ]),
            )
            .order_by(models.AuditLog.timestamp.desc())
            .all()
        )
        action_details = {
            "visit_card_issue": "Выдача карты на визит",
            "visit_card_return": "Возврат карты и нормальное закрытие визита",
            "visit_card_lost": "Карта отмечена как потерянная во время визита",
            "visit_card_reissue": "Карта перевыпущена внутри активного визита",
            "visit_service_close": "Визит закрыт сервисным сценарием без возврата карты",
        }
        for log in audit_logs:
            history_items.append(
                schemas.HistoryItem(
                    timestamp=log.timestamp,
                    type=log.action,
                    amount=Decimal("0.00"),
                    details=action_details.get(log.action, log.action),
                )
            )

    history_items.sort(key=lambda item: item.timestamp, reverse=True)
    return schemas.GuestHistoryResponse(guest_id=guest_id, history=history_items)
