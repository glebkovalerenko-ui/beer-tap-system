# backend/api/cards.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import schemas
import security
from database import get_db
from crud import card_crud

router = APIRouter(
    prefix="/cards",
    tags=["Cards"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Card, status_code=status.HTTP_201_CREATED, summary="Зарегистрировать новую карту")
def create_card(card: schemas.CardCreate, db: Session = Depends(get_db)):
    """
    Регистрирует новую физическую RFID-карту в системе.

    Карта создается со статусом 'inactive' и еще не привязана ни к одному гостю.
    UID карты (`card_uid`) должен быть уникальным.
    """
    return card_crud.create_card(db=db, card=card)

@router.get("/", response_model=List[schemas.Card], summary="Получить список всех карт")
def read_cards(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Возвращает список всех RFID-карт, когда-либо зарегистрированных в системе,
    с поддержкой пагинации.
    """
    return card_crud.get_cards(db, skip=skip, limit=limit)

@router.put("/{card_uid}/status", response_model=schemas.Card, summary="Изменить статус карты")
def update_card_status(
    card_uid: str, 
    card_update: schemas.CardStatusUpdate, 
    db: Session = Depends(get_db)
):
    """
    Обновляет статус карты.

    Используется, например, для блокировки утерянной карты (статус 'lost').
    Допустимые статусы определены в бизнес-логике.
    """
    db_card = card_crud.update_card_status(db, card_uid=card_uid, new_status=card_update.status)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return db_card