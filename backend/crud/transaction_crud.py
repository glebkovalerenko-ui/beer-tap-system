import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from crud import guest_crud, visit_crud
from pos_adapter import get_pos_adapter


def create_topup_transaction(db: Session, guest_id: uuid.UUID, topup_data: schemas.TopUpRequest):
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    active_visit = visit_crud.get_active_visit_by_guest_id(db=db, guest_id=guest_id)
    transaction = models.Transaction(
        guest_id=guest_id,
        visit_id=active_visit.visit_id if active_visit else None,
        amount=topup_data.amount,
        type="top-up",
        payment_method=topup_data.payment_method,
    )
    db.add(transaction)
    db_guest.balance += topup_data.amount

    db.flush()
    db.refresh(transaction)
    get_pos_adapter().notify_topup(db=db, transaction=transaction, guest=db_guest)

    db.commit()
    db.refresh(db_guest)
    return db_guest


def create_refund_transaction(db: Session, guest_id: uuid.UUID, refund_data: schemas.RefundRequest):
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    if db_guest.balance < refund_data.amount:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient guest balance for refund")

    active_visit = visit_crud.get_active_visit_by_guest_id(db=db, guest_id=guest_id)
    refund_amount = -refund_data.amount
    transaction = models.Transaction(
        guest_id=guest_id,
        visit_id=active_visit.visit_id if active_visit else None,
        amount=refund_amount,
        type="refund",
        payment_method=refund_data.payment_method,
    )
    db.add(transaction)
    db_guest.balance += refund_amount

    db.flush()
    db.refresh(transaction)
    get_pos_adapter().notify_refund(db=db, transaction=transaction, guest=db_guest)

    db.commit()
    db.refresh(db_guest)
    return db_guest
