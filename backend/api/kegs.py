# backend/api/kegs.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import schemas, security
from crud import keg_crud
from database import get_db

router = APIRouter(
    prefix="/api/kegs",
    tags=["Kegs"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Keg, status_code=201, summary="Зарегистрировать новую кегу")
def create_keg(keg: schemas.KegCreate, db: Session = Depends(get_db)):
    """
    Регистрирует новую физическую кегу в системе.

    Требует указания существующего `beverage_id` для привязки к напитку.
    Автоматически устанавливает `current_volume_ml` равным `initial_volume_ml`.
    """
    return keg_crud.create_keg(db=db, keg=keg)

@router.get("/", response_model=List[schemas.Keg], summary="Получить список всех кег")
def read_kegs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Возвращает список всех кег в системе с поддержкой пагинации.
    Включает информацию о связанном напитке.
    """
    return keg_crud.get_kegs(db, skip=skip, limit=limit)

@router.get("/{keg_id}", response_model=schemas.Keg, summary="Получить кегу по ID")
def read_keg(keg_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Получает детальную информацию о конкретной кеге по ее UUID.
    """
    return keg_crud.get_keg(db, keg_id=keg_id)

@router.put("/{keg_id}", response_model=schemas.Keg, summary="Обновить статус кеги")
def update_keg(keg_id: uuid.UUID, keg_update: schemas.KegUpdate, db: Session = Depends(get_db)):
    """
    Обновляет информацию о кеге (на данный момент, только ее статус).
    """
    return keg_crud.update_keg(db=db, keg_id=keg_id, keg_update=keg_update)

@router.delete("/{keg_id}", status_code=204, summary="Удалить кегу")
def delete_keg(keg_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Удаляет кегу из системы.

    **Бизнес-правило:** Запрещено удалять кегу, которая в данный момент
    подключена к крану (статус 'in_use').
    """
    keg_crud.delete_keg(db=db, keg_id=keg_id)
    return # Возвращаем пустой ответ 204 No Content для DELETE операций