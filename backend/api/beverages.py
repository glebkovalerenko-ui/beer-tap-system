# backend/api/beverages.py
from typing import List, Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
from crud import beverage_crud
from database import get_db
import security

router = APIRouter(
    prefix="/beverages",
    tags=["Beverages"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Beverage, status_code=201, summary="Создать новый напиток")
def create_beverage(
    beverage: schemas.BeverageCreate, 
    db: Session = Depends(get_db)
):
    """
    Создает новую запись о напитке в глобальном справочнике.

    Используется для добавления нового пива или другого напитка в ассортимент бара.
    Название напитка (`name`) должно быть уникальным.
    """
    return beverage_crud.create_beverage(db=db, beverage=beverage)

@router.get("/", response_model=List[schemas.Beverage], summary="Получить список напитков")
def read_beverages(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Возвращает список всех напитков, зарегистрированных в системе,
    с поддержкой пагинации.
    """
    return beverage_crud.get_beverages(db, skip=skip, limit=limit)

@router.get("/{beverage_id}", response_model=schemas.Beverage, summary="Получить напиток по ID")
def read_beverage(
    beverage_id: uuid.UUID, # ИСПРАВЛЕНИЕ: Тип ID изменен на UUID в соответствии с моделью
    db: Session = Depends(get_db)
):
    """
    Получает детальную информацию о конкретном напитке по его уникальному идентификатору (UUID).
    """
    db_beverage = beverage_crud.get_beverage(db, beverage_id=beverage_id)
    # Обработка ошибки 404 Not Found встроена в crud-функцию
    return db_beverage