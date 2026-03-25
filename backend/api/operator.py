from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import schemas
import security
from crud import operator_crud
from database import get_db


router = APIRouter(
    prefix="/operator",
    tags=["Operator"],
    dependencies=[Depends(security.get_current_user)],
)


@router.get("/today", response_model=schemas.OperatorTodayModel, summary="Operator-first today overview")
def read_operator_today(
    current_user: dict = Depends(security.require_permissions("taps_view")),
    db: Session = Depends(get_db),
):
    return operator_crud.get_operator_today(db=db, current_user=current_user)


@router.get("/taps", response_model=list[schemas.TapWorkspaceCard], summary="Operator tap workspace")
def read_operator_taps(
    current_user: dict = Depends(security.require_permissions("taps_view")),
    db: Session = Depends(get_db),
):
    return operator_crud.get_operator_taps(db=db, current_user=current_user)


@router.get("/taps/{tap_id}", response_model=schemas.TapDrawerModel, summary="Operator tap drawer detail")
def read_operator_tap_detail(
    tap_id: int,
    current_user: dict = Depends(security.require_permissions("taps_view")),
    db: Session = Depends(get_db),
):
    return operator_crud.get_operator_tap_detail(db=db, tap_id=tap_id, current_user=current_user)


@router.get("/cards/lookup", response_model=schemas.CardGuestContextModel, summary="Operator card lookup context")
def read_operator_card_lookup(
    query: str = Query(..., min_length=1),
    current_user: dict = Depends(security.require_permissions("cards_lookup")),
    db: Session = Depends(get_db),
):
    return operator_crud.lookup_operator_card_context(db=db, query=query, current_user=current_user)
