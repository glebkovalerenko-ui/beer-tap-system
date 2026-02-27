import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

import schemas
import security
from crud import shift_crud, visit_crud
from database import get_db
from runtime_diagnostics import get_alembic_revision, get_db_identity, get_request_id

router = APIRouter(
    prefix="/visits",
    tags=["Visits"],
)
logger = logging.getLogger("m4.runtime.authorize")


@router.post("/open", response_model=schemas.Visit, summary="Open active visit")
def open_visit(
    payload: schemas.VisitOpenRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    shift_crud.ensure_open_shift(db)
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    shift_crud.ensure_open_shift(db)
    request_id = get_request_id(request)
    db_identity = get_db_identity(db)
    alembic_revision = get_alembic_revision(db)
    actor_id = current_user["username"] if current_user else "operator"

    try:
        visit, pending_outcome = visit_crud.authorize_pour_lock(
            db=db,
            card_uid=payload.card_uid,
            tap_id=payload.tap_id,
            actor_id=actor_id,
        )
    except HTTPException as exc:
        outcome = "authorize_rejected"
        if exc.status_code == status.HTTP_403_FORBIDDEN and isinstance(exc.detail, dict):
            if exc.detail.get("reason") == "lost_card":
                outcome = "rejected_lost_card"
        elif exc.status_code == status.HTTP_409_CONFLICT and isinstance(exc.detail, str):
            if exc.detail.startswith("No active visit for Card "):
                outcome = "rejected_no_active_visit"
            elif exc.detail.startswith("Card already in use on Tap "):
                outcome = "rejected_tap_mismatch"

        logger.warning(
            "authorize_pour request_id=%s db_identity=%s alembic_revision=%s actor=%s card_uid=%s tap_id=%s outcome=%s status_code=%s detail=%s",
            request_id,
            db_identity,
            alembic_revision,
            actor_id,
            payload.card_uid,
            payload.tap_id,
            outcome,
            exc.status_code,
            exc.detail,
        )
        raise

    logger.info(
        "authorize_pour request_id=%s db_identity=%s alembic_revision=%s actor=%s card_uid=%s tap_id=%s visit_id=%s outcome=%s",
        request_id,
        db_identity,
        alembic_revision,
        actor_id,
        payload.card_uid,
        payload.tap_id,
        visit.visit_id,
        pending_outcome,
    )
    return schemas.VisitPourAuthorizeResponse(allowed=True, visit=visit)


@router.post(
    "/{visit_id}/report-lost-card",
    response_model=schemas.VisitReportLostCardResponse,
    summary="Report card as lost from active visit",
)
def report_lost_card_from_visit(
    visit_id: uuid.UUID,
    payload: schemas.VisitReportLostCardRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    visit, lost_card, created = visit_crud.report_lost_card_from_visit(
        db=db,
        visit_id=visit_id,
        reason=payload.reason,
        comment=payload.comment,
        actor_id=current_user["username"] if current_user else None,
    )
    return schemas.VisitReportLostCardResponse(
        visit=visit,
        lost_card=lost_card,
        lost=True,
        already_marked=not created,
    )


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


@router.post("/{visit_id}/reconcile-pour", response_model=schemas.Visit, summary="Manually reconcile pour and unlock visit")
def reconcile_pour(
    visit_id: uuid.UUID,
    payload: schemas.VisitReconcilePourRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return visit_crud.reconcile_pour(
        db=db,
        visit_id=visit_id,
        tap_id=payload.tap_id,
        short_id=payload.short_id,
        volume_ml=payload.volume_ml,
        amount=payload.amount,
        duration_ms=payload.duration_ms,
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


@router.get("/active", response_model=list[schemas.VisitActiveListItem], summary="List all active visits")
def list_active_visits(
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return visit_crud.get_active_visits_list(db=db)


@router.post("/{visit_id}/assign-card", response_model=schemas.Visit, summary="Assign card to active visit")
def assign_card_to_visit(
    visit_id: uuid.UUID,
    payload: schemas.VisitAssignCardRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return visit_crud.assign_card_to_active_visit(db=db, visit_id=visit_id, card_uid=payload.card_uid)
