# backend/api/system.py

from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import schemas
import security
from crud import system_crud
from database import get_db

router = APIRouter(
    prefix="/system",
    tags=["System"]
)

EMERGENCY_STOP_KEY = "emergency_stop_enabled"

@router.get("/status", response_model=schemas.SystemStateItem, summary="Получить статус экстренной остановки")
def get_system_status(db: Session = Depends(get_db)):
    """
    Возвращает текущее состояние флага экстренной остановки.

    Этот эндпоинт является публичным и оптимизирован для частого опроса
    контроллерами (RPi) для проверки глобального состояния системы.
    """
    state = system_crud.get_state(db, EMERGENCY_STOP_KEY, "false")
    return state


@router.post("/emergency_stop", response_model=schemas.SystemStateItem, summary="Включить/выключить экстренную остановку")
def set_emergency_stop(
    state_update: schemas.SystemStateUpdate,
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
    
    updated_state = system_crud.set_state(
        db=db,
        key=EMERGENCY_STOP_KEY,
        value=state_update.value
    )
    return updated_state


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