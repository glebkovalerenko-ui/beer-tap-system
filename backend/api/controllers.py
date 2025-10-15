# backend/api/controllers.py
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Абсолютные импорты
import schemas
import security
from crud import controller_crud
from database import get_db

router = APIRouter(
    prefix="/api/controllers",
    tags=["Controllers"]
)

@router.post("/register", response_model=schemas.Controller, summary="Зарегистрировать контроллер (check-in)")
def register_controller(
    controller: schemas.ControllerRegister, 
    db: Session = Depends(get_db)
):
    """
    Эндпоинт для регистрации или обновления данных контроллера (check-in).

    **Логика (Upsert):**
    - Если контроллер с таким `controller_id` не найден, он будет создан.
    - Если контроллер уже существует, его данные (`ip_address`, `firmware_version`)
      и время последнего визита (`last_seen`) будут обновлены.

    Этот эндпоинт является публичным и предназначен для использования RPi-контроллерами.
    """
    return controller_crud.register_controller(db=db, controller=controller)


@router.get("/", response_model=List[schemas.Controller], summary="Получить список контроллеров")
def read_controllers(
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Возвращает список всех зарегистрированных контроллеров и их последнее состояние.

    Доступно только для аутентифицированных пользователей (администраторов).
    """
    return controller_crud.get_controllers(db)