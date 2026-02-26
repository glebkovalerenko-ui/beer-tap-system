from datetime import date
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import schemas
import security
from crud import shift_crud, shift_report_crud
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


@router.get(
    "/{shift_id}/reports/x",
    response_model=schemas.ShiftReportPayload,
    summary="Compute X report for shift",
)
def get_x_report(
    shift_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_report_crud.get_x_report_for_shift(db=db, shift_id=shift_id)


@router.post(
    "/{shift_id}/reports/z",
    response_model=schemas.ShiftReportDocument,
    summary="Create or get Z report for closed shift",
)
def create_z_report(
    shift_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_report_crud.create_or_get_z_report(db=db, shift_id=shift_id)


@router.get(
    "/{shift_id}/reports/z",
    response_model=schemas.ShiftReportDocument,
    summary="Get existing Z report for shift",
)
def get_z_report(
    shift_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_report_crud.get_z_report(db=db, shift_id=shift_id)


@router.get(
    "/reports/z",
    response_model=list[schemas.ShiftZReportListItem],
    summary="List Z reports by generated date range",
)
def list_z_reports(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return shift_report_crud.list_z_reports_by_date(
        db=db,
        from_date=from_date,
        to_date=to_date,
    )
