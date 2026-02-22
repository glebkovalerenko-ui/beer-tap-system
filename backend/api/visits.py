from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import schemas
import security
from crud import visit_crud
from database import get_db

router = APIRouter(
    prefix="/visits",
    tags=["Visits"],
)


@router.post("/open", response_model=schemas.Visit, summary="Open active visit")
def open_visit(
    payload: schemas.VisitOpenRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return visit_crud.open_visit(db=db, guest_id=payload.guest_id, card_uid=payload.card_uid)


@router.post("/{visit_id}/close", response_model=schemas.Visit, summary="Close active visit")
def close_visit(
    visit_id: uuid.UUID,
    payload: schemas.VisitCloseRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return visit_crud.close_visit(
        db=db,
        visit_id=visit_id,
        closed_reason=payload.closed_reason,
        card_returned=payload.card_returned,
    )


@router.post("/authorize-pour", response_model=schemas.VisitPourAuthorizeResponse, summary="Authorize pour and set active tap lock")
def authorize_pour(
    payload: schemas.VisitPourAuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    visit = visit_crud.authorize_pour_lock(
        db=db,
        card_uid=payload.card_uid,
        tap_id=payload.tap_id,
        actor_id=current_user["username"] if current_user else "operator",
    )
    return schemas.VisitPourAuthorizeResponse(allowed=True, visit=visit)


@router.post("/{visit_id}/force-unlock", response_model=schemas.Visit, summary="Force unlock active tap for visit")
def force_unlock_visit(
    visit_id: uuid.UUID,
    payload: schemas.VisitForceUnlockRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return visit_crud.force_unlock_visit(
        db=db,
        visit_id=visit_id,
        reason=payload.reason,
        comment=payload.comment,
        actor_id=current_user["username"] if current_user else "operator",
    )


@router.get("/active/by-card/{card_uid}", response_model=schemas.Visit, summary="Get active visit by card UID")
def get_active_visit_by_card(
    card_uid: str,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    visit = visit_crud.get_active_visit_by_card_uid(db=db, card_uid=card_uid)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active visit not found")
    return visit


@router.get("/active/by-guest/{guest_id}", response_model=schemas.Visit, summary="Get active visit by guest")
def get_active_visit_by_guest(
    guest_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    visit = visit_crud.get_active_visit_by_guest_id(db=db, guest_id=guest_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active visit not found")
    return visit


@router.get("/active/search", response_model=schemas.Visit, summary="Search active visit by guest FIO/phone")
def search_active_visit(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    visit = visit_crud.search_active_visit_by_guest_query(db=db, query=q)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active visit not found")
    return visit
