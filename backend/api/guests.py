# backend/api/guests.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import schemas
import security
# +++ НАЧАЛО ИЗМЕНЕНИЙ: Импортируем CRUD для карт +++
from crud import guest_crud, transaction_crud, card_crud
# +++ КОНЕЦ ИЗМЕНЕНИЙ +++
from database import get_db
import uuid

router = APIRouter(
    prefix="/api/guests",
    tags=["Guests"],
    dependencies=[Depends(security.get_current_user)]
)

# ... (остальные эндпоинты: create_guest, read_guests, read_guest, update_guest остаются без изменений) ...
@router.post("/", response_model=schemas.Guest, status_code=status.HTTP_201_CREATED, summary="Создать нового гостя")
def create_guest(guest: schemas.GuestCreate, db: Session = Depends(get_db)):
    return guest_crud.create_guest(db=db, guest=guest)

@router.get("/", response_model=List[schemas.Guest], summary="Получить список гостей")
def read_guests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return guest_crud.get_guests(db, skip=skip, limit=limit)

@router.get("/{guest_id}", response_model=schemas.Guest, summary="Получить гостя по ID")
def read_guest(guest_id: uuid.UUID, db: Session = Depends(get_db)):
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if db_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return db_guest

@router.put("/{guest_id}", response_model=schemas.Guest, summary="Обновить данные гостя")
def update_guest(guest_id: uuid.UUID, guest_update: schemas.GuestUpdate, db: Session = Depends(get_db)):
    updated_guest = guest_crud.update_guest(db=db, guest_id=guest_id, guest_update=guest_update)
    if updated_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return updated_guest


# +++ НАЧАЛО ИЗМЕНЕНИЙ: Полностью переработанная логика привязки карты +++
@router.post("/{guest_id}/cards", response_model=schemas.Guest, summary="Привязать или зарегистрировать и привязать карту к гостю")
def assign_or_register_card_to_guest(guest_id: uuid.UUID, card_assign: schemas.CardAssign, db: Session = Depends(get_db)):
    """
    Привязывает карту к гостю. Реализует логику "найти или создать".

    1.  Проверяет, существует ли гость.
    2.  Ищет карту по `card_uid`.
    3.  Если карта найдена:
        - Если она активна и привязана к другому гостю, возвращает ошибку 409 Conflict.
        - Если она неактивна, привязывает ее к текущему гостю.
    4.  Если карта не найдена:
        - Создает новую карту в базе данных.
        - Сразу привязывает ее к текущему гостю.
    5.  Возвращает обновленный объект гостя.
    """
    # Шаг 1: Проверить, существует ли гость
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    # Шаг 2: Искать карту по UID, используя нашу CRUD-функцию
    db_card = card_crud.get_card_by_uid(db, uid=card_assign.card_uid)

    if db_card:
        # Шаг 3: Карта найдена
        if db_card.guest_id and db_card.guest_id != guest_id:
            # Карта привязана к другому гостю
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Card with UID {card_assign.card_uid} is already assigned to another guest."
            )
        # Привязываем существующую карту, используя новую CRUD-функцию
        card_crud.assign_card_to_guest(db, db_card=db_card, guest_id=guest_id)
    else:
        # Шаг 4: Карта не найдена - создаем и сразу привязываем, используя новую CRUD-функцию
        new_card_schema = schemas.CardCreate(card_uid=card_assign.card_uid)
        card_crud.create_and_assign_card(db, card=new_card_schema, guest_id=guest_id)

    # Шаг 5: Возвращаем обновленного гостя
    db.refresh(db_guest)
    return db_guest
# +++ КОНЕЦ ИЗМЕНЕНИЙ +++


# ... (остальные эндпоинты: unassign_card, topup, history остаются без изменений) ...
@router.delete("/{guest_id}/cards/{card_uid}", response_model=schemas.Guest, summary="Отвязать карту от гостя")
def unassign_card_from_guest(guest_id: uuid.UUID, card_uid: str, db: Session = Depends(get_db)):
    return guest_crud.unassign_card_from_guest(db=db, guest_id=guest_id, card_uid=card_uid)

@router.post("/{guest_id}/topup", 
             response_model=schemas.Guest, 
             summary="Пополнить баланс гостя")
def topup_guest_balance(guest_id: uuid.UUID, topup_data: schemas.TopUpRequest, db: Session = Depends(get_db)):
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
    return guest_crud.get_guest_history(
        db=db, guest_id=guest_id, start_date=start_date, end_date=end_date
    )