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
    request_id = get_request_id(request)
    db_identity = get_db_identity(db)
    alembic_revision = get_alembic_revision(db)
    actor_id = current_user["username"] if current_user else "operator"

    try:
        shift_crud.ensure_open_shift(db)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN and exc.detail == "Shift is closed":
            outcome = "rejected_shift_closed"
            detail = {"reason": "shift_closed", "message": "Shift is closed"}
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
                detail,
            )
            raise HTTPException(status_code=exc.status_code, detail=detail) from exc
        raise

    try:
        visit, pending_outcome, authorize_context = visit_crud.authorize_pour_lock(
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
            elif exc.detail.get("reason") == "insufficient_funds":
                outcome = "rejected_insufficient_funds"
            elif exc.detail.get("reason") == "shift_closed":
                outcome = "rejected_shift_closed"
        elif exc.status_code == status.HTTP_409_CONFLICT:
            if isinstance(exc.detail, dict) and exc.detail.get("reason") == "no_active_visit":
                outcome = "rejected_no_active_visit"
            elif isinstance(exc.detail, str) and exc.detail.startswith("No active visit for Card "):
                outcome = "rejected_no_active_visit"
            elif isinstance(exc.detail, dict) and exc.detail.get("reason") == "card_in_use_on_other_tap":
                outcome = "rejected_tap_mismatch"
            elif isinstance(exc.detail, str) and exc.detail.startswith("Card already in use on Tap "):
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
    return schemas.VisitPourAuthorizeResponse(
        allowed=True,
        visit=visit,
        reason=None,
        min_start_ml=authorize_context["min_start_ml"],
        max_volume_ml=authorize_context["max_volume_ml"],
        price_per_ml_cents=authorize_context["price_per_ml_cents"],
        balance_cents=authorize_context["balance_cents"],
        allowed_overdraft_cents=authorize_context["allowed_overdraft_cents"],
        safety_ml=authorize_context["safety_ml"],
        lock_set_at=visit.lock_set_at,
    )


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
