from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import schemas
import security
from crud import shift_crud
from database import get_db

router = APIRouter(
    prefix="/shifts",
    tags=["Shifts"],
)


@router.post("/open", response_model=schemas.Shift, summary="Open shift")
def open_shift(
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_crud.open_shift(
        db=db,
        opened_by=current_user["username"] if current_user else None,
    )


@router.post("/close", response_model=schemas.Shift, summary="Close shift")
def close_shift(
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_crud.close_shift(
        db=db,
        closed_by=current_user["username"] if current_user else None,
    )


@router.get("/current", response_model=schemas.ShiftCurrentResponse, summary="Get current shift state")
def get_current_shift(
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_crud.get_current_shift_state(db=db)
