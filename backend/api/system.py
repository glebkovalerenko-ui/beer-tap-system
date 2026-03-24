# backend/api/system.py

from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import schemas
import security
from crud import system_crud, incident_crud
from database import get_db

router = APIRouter(
    prefix="/system",
    tags=["System"]
)

EMERGENCY_STOP_KEY = "emergency_stop_enabled"

@router.get("/status", response_model=schemas.SystemOperationalSummary, summary="Получить operational summary системы")
def get_system_status(db: Session = Depends(get_db)):
    return incident_crud.get_system_summary(db)


@router.post("/emergency_stop", response_model=schemas.SystemOperationalSummary, summary="Включить/выключить экстренную остановку")
def set_emergency_stop(
    state_update: schemas.SystemStateUpdate,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("maintenance_actions"))],
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Включает или выключает режим экстренной остановки для всей системы.

    Принимает значение 'true' или 'false'.
    Доступно только для аутентифицированных пользователей.
    """
    if state_update.value not in ["true", "false"]:
        raise HTTPException(status_code=400, detail="Value must be 'true' or 'false'")
    
    system_crud.set_state(
        db=db,
        key=EMERGENCY_STOP_KEY,
        value=state_update.value
    )
    return incident_crud.get_system_summary(db)


@router.get("/states/all", response_model=List[schemas.SystemStateItem], summary="Получить все флаги состояния системы", include_in_schema=False)
def get_all_system_states(db: Session = Depends(get_db)):
    """
    Возвращает все глобальные флаги состояния системы.
    Используется для отладки.
    """
    states = system_crud.get_all_states(db)
    # Гарантируем, что флаг экстренной остановки всегда присутствует в ответе
    if not any(s.key == EMERGENCY_STOP_KEY for s in states):
        emergency_state = system_crud.get_state(db, EMERGENCY_STOP_KEY, "false")
        states.append(emergency_state)
    
    return states
