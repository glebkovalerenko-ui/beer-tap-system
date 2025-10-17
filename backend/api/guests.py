# backend/api/guests.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
from datetime import date
import schemas
import security
from crud import guest_crud, transaction_crud
from database import get_db
import uuid

router = APIRouter(
    prefix="/api/guests",
    tags=["Guests"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Guest, status_code=status.HTTP_201_CREATED, summary="Создать нового гостя")
def create_guest(guest: schemas.GuestCreate, db: Session = Depends(get_db)):
    """
    Регистрирует нового гостя в системе.
    Телефонный номер и номер документа должны быть уникальными.
    """
    return guest_crud.create_guest(db=db, guest=guest)

@router.get("/", response_model=List[schemas.Guest], summary="Получить список гостей")
def read_guests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Возвращает список гостей с поддержкой пагинации.
    """
    return guest_crud.get_guests(db, skip=skip, limit=limit)

@router.get("/{guest_id}", response_model=schemas.Guest, summary="Получить гостя по ID")
def read_guest(guest_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Получает детальную информацию о госте по его UUID.
    """
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if db_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return db_guest

# +++ НАЧАЛО ИЗМЕНЕНИЙ +++
@router.put("/{guest_id}", response_model=schemas.Guest, summary="Обновить данные гостя")
def update_guest(guest_id: uuid.UUID, guest_update: schemas.GuestUpdate, db: Session = Depends(get_db)):
    """
    Обновляет информацию о существующем госте.

    Позволяет частично обновлять данные: можно передать только те поля,
    которые необходимо изменить.
    """
    updated_guest = guest_crud.update_guest(db=db, guest_id=guest_id, guest_update=guest_update)
    if updated_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return updated_guest
# +++ КОНЕЦ ИЗМЕНЕНИЙ +++

@router.post("/{guest_id}/cards", response_model=schemas.Guest, summary="Привязать карту к гостю")
def assign_card_to_guest(guest_id: uuid.UUID, card_assign: schemas.CardAssign, db: Session = Depends(get_db)):
    """
    Привязывает существующую, неактивную RFID-карту к гостю.
    Карта должна быть предварительно зарегистрирована в системе.
    """
    return guest_crud.assign_card_to_guest(db=db, guest_id=guest_id, uid=card_assign.card_uid)

@router.delete("/{guest_id}/cards/{card_uid}", response_model=schemas.Guest, summary="Отвязать карту от гостя")
def unassign_card_from_guest(guest_id: uuid.UUID, card_uid: str, db: Session = Depends(get_db)):
    """
    Отвязывает RFID-карту от гостя, переводя ее в статус 'inactive'.
    """
    return guest_crud.unassign_card_from_guest(db=db, guest_id=guest_id, card_uid=card_uid)

@router.post("/{guest_id}/topup", 
             response_model=schemas.Guest, 
             summary="Пополнить баланс гостя")
def topup_guest_balance(guest_id: uuid.UUID, topup_data: schemas.TopUpRequest, db: Session = Depends(get_db)):
    """
    Создает финансовую транзакцию для пополнения баланса.
    Эта операция атомарна: создается запись в `transactions` и обновляется
    поле `balance` у гостя.

    Возвращает обновленный объект гостя.
    """
    return transaction_crud.create_topup_transaction(db=db, guest_id=guest_id, topup_data=topup_data)

@router.get("/{guest_id}/history",
            response_model=schemas.GuestHistoryResponse,
            summary="Получить историю операций гостя")
def get_guest_history(
    guest_id: uuid.UUID, 
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Возвращает полную, отсортированную историю операций гостя (пополнения и наливы)
    за указанный период времени.
    """
    return guest_crud.get_guest_history(
        db=db, guest_id=guest_id, start_date=start_date, end_date=end_date
    )