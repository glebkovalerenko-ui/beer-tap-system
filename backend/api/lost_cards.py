from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import schemas
import security
from crud import lost_card_crud
from database import get_db


router = APIRouter(
    prefix="/lost-cards",
    tags=["LostCards"],
)


@router.post("", response_model=schemas.LostCard, summary="Create lost card record (idempotent by card_uid)")
@router.post("/", response_model=schemas.LostCard, include_in_schema=False)
def create_lost_card(
    payload: schemas.LostCardCreateRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    lost_card, _created = lost_card_crud.create_lost_card_idempotent(
        db=db,
        card_uid=payload.card_uid,
        reported_by=payload.reported_by or (current_user["username"] if current_user else None),
        reason=payload.reason,
        comment=payload.comment,
        visit_id=payload.visit_id,
        guest_id=payload.guest_id,
    )
    return lost_card


@router.get("", response_model=list[schemas.LostCard], summary="List lost cards")
@router.get("/", response_model=list[schemas.LostCard], include_in_schema=False)
def list_lost_cards(
    uid: str | None = Query(default=None, min_length=1),
    reported_from: datetime | None = Query(default=None),
    reported_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return lost_card_crud.list_lost_cards(
        db=db,
        card_uid=uid,
        reported_from=reported_from,
        reported_to=reported_to,
    )


@router.post("/{card_uid}/restore", response_model=schemas.LostCardRestoreResponse, summary="Restore lost card")
def restore_lost_card(
    card_uid: str,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    restored_uid = lost_card_crud.restore_lost_card(db=db, card_uid=card_uid)
    if not restored_uid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lost card not found")
    return schemas.LostCardRestoreResponse(card_uid=restored_uid, restored=True)
