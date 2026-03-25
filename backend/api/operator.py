import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session

import schemas
import security
from crud import operator_crud
from database import get_db
from operator_stream import operator_stream_hub


router = APIRouter(
    prefix="/operator",
    tags=["Operator"],
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


@router.get("/sessions", response_model=schemas.OperatorSessionJournalModel, summary="Operator session journal")
def read_operator_sessions(
    period_preset: str = Query(default="today", alias="period_preset"),
    date_from: str | None = Query(default=None, alias="date_from"),
    date_to: str | None = Query(default=None, alias="date_to"),
    tap_id: int | None = Query(default=None, alias="tap_id"),
    status_filter: str | None = Query(default=None, alias="status"),
    card_uid: str | None = Query(default=None, alias="card_uid"),
    completion_source: str | None = Query(default=None, alias="completion_source"),
    incident_only: bool = Query(default=False, alias="incident_only"),
    unsynced_only: bool = Query(default=False, alias="unsynced_only"),
    zero_volume_abort_only: bool = Query(default=False, alias="zero_volume_abort_only"),
    active_only: bool = Query(default=False, alias="active_only"),
    current_user: dict = Depends(security.require_permissions("sessions_view")),
    db: Session = Depends(get_db),
):
    parsed_filters = schemas.OperatorSessionJournalFilterParams(
        period_preset=period_preset,
        date_from=date_from,
        date_to=date_to,
        tap_id=tap_id,
        status=status_filter,
        card_uid=card_uid,
        completion_source=completion_source,
        incident_only=incident_only,
        unsynced_only=unsynced_only,
        zero_volume_abort_only=zero_volume_abort_only,
        active_only=active_only,
    )
    return operator_crud.get_operator_sessions(
        db=db,
        filters=parsed_filters,
        current_user=current_user,
    )


@router.get("/sessions/{visit_id}", response_model=schemas.OperatorSessionDetailModel, summary="Operator session detail")
def read_operator_session_detail(
    visit_id: uuid.UUID,
    current_user: dict = Depends(security.require_permissions("sessions_view")),
    db: Session = Depends(get_db),
):
    return operator_crud.get_operator_session_detail(
        db=db,
        visit_id=visit_id,
        current_user=current_user,
    )


@router.get("/system", response_model=schemas.OperatorSystemHealthModel, summary="Operator system health")
def read_operator_system(
    current_user: dict = Depends(security.require_permissions("system_health_view")),
    db: Session = Depends(get_db),
):
    return operator_crud.get_operator_system_health(db=db, current_user=current_user)


@router.post("/stream-ticket", response_model=schemas.OperatorStreamTicket, summary="Issue operator stream ticket")
def create_operator_stream_ticket(
    current_user: dict = Depends(security.get_current_user),
):
    return operator_stream_hub.issue_ticket(current_user)


@router.websocket("/stream")
async def operator_stream(websocket: WebSocket, ticket: str):
    current_user = operator_stream_hub.consume_ticket(ticket)
    if current_user is None:
        await websocket.close(code=4401)
        return

    await operator_stream_hub.connect(websocket)
    await operator_stream_hub.send_hello(websocket)
    heartbeat_task = asyncio.create_task(operator_stream_hub.heartbeat_loop(websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await operator_stream_hub.disconnect(websocket)
