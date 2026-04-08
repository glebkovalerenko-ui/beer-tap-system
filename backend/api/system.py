from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import schemas
import security
from crud import incident_crud, system_crud
from database import get_db
from operator_stream import operator_stream_hub


router = APIRouter(
    prefix="/system",
    tags=["System"],
)

EMERGENCY_STOP_KEY = "emergency_stop_enabled"


@router.get("/status", response_model=schemas.SystemOperationalSummary, summary="Get operational system summary")
def get_system_status(db: Session = Depends(get_db)):
    return incident_crud.get_system_summary(db)


@router.post("/emergency_stop", response_model=schemas.SystemOperationalSummary, summary="Set emergency stop")
def set_emergency_stop(
    state_update: schemas.SystemStateUpdate,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("maintenance_actions"))],
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)],
    db: Session = Depends(get_db),
):
    if state_update.value not in ["true", "false"]:
        raise HTTPException(status_code=400, detail="Value must be 'true' or 'false'")

    system_crud.set_state(
        db=db,
        key=EMERGENCY_STOP_KEY,
        value=state_update.value,
    )
    operator_stream_hub.emit_invalidation(resource="system", severity="critical", reason="emergency_stop_changed")
    operator_stream_hub.emit_invalidation(resource="today", severity="critical", reason="emergency_stop_changed")
    operator_stream_hub.emit_invalidation(resource="taps", severity="critical", reason="emergency_stop_changed")
    operator_stream_hub.emit_invalidation(resource="incident", severity="critical", reason="emergency_stop_changed")
    return incident_crud.get_system_summary(db)


@router.get(
    "/states/all",
    response_model=list[schemas.SystemStateItem],
    summary="Get all system flags",
    include_in_schema=False,
)
def get_all_system_states(
    _permission_guard: Annotated[dict, Depends(security.require_permissions("debug_tools"))],
    db: Session = Depends(get_db),
):
    states = system_crud.get_all_states(db)
    if not any(state.key == EMERGENCY_STOP_KEY for state in states):
        emergency_state = system_crud.get_state(db, EMERGENCY_STOP_KEY, "false")
        states.append(emergency_state)

    return states
