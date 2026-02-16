# backend/api/guests.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
# --- ИЗМЕНЕНИЕ: Добавляем Annotated для явного указания зависимости ---
from typing import List, Optional, Annotated 
from datetime import date
import schemas
import security
from crud import guest_crud, transaction_crud, card_crud
from database import get_db
import uuid

router = APIRouter(
    prefix="/guests",
    tags=["Guests"],
    # --- ИЗМЕНЕНИЕ: Убираем глобальную зависимость отсюда ---
    # dependencies=[Depends(security.get_current_user)] 
)

# --- ВАЖНО: Теперь мы добавляем зависимость в КАЖДЫЙ эндпоинт, который меняет данные. ---

@router.post("", response_model=schemas.Guest, status_code=status.HTTP_201_CREATED, summary="Создать нового гостя")
def create_guest(
    guest: schemas.GuestCreate, 
    db: Session = Depends(get_db),
    # --- ИЗМЕНЕНИЕ: Явно запрашиваем текущего пользователя. Это активирует аудит. ---
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    # `current_user` здесь не используется, но его присутствие в сигнатуре КЛЮЧЕВОЕ.
    return guest_crud.create_guest(db=db, guest=guest)

@router.get("", response_model=List[schemas.Guest], summary="Получить список гостей")
def read_guests(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    return guest_crud.get_guests(db, skip=skip, limit=limit)

@router.get("/{guest_id}", response_model=schemas.Guest, summary="Получить гостя по ID")
def read_guest(
    guest_id: uuid.UUID, 
    db: Session = Depends(get_db)
):
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if db_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return db_guest

@router.put("/{guest_id}", response_model=schemas.Guest, summary="Обновить данные гостя")
def update_guest(
    guest_id: uuid.UUID, 
    guest_update: schemas.GuestUpdate, 
    db: Session = Depends(get_db),
    # --- ИЗМЕНЕНИЕ: Явно запрашиваем текущего пользователя. ---
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    updated_guest = guest_crud.update_guest(db=db, guest_id=guest_id, guest_update=guest_update)
    if updated_guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
    return updated_guest

@router.post("/{guest_id}/cards", response_model=schemas.Guest, summary="Привязать или зарегистрировать и привязать карту к гостю")
def assign_or_register_card_to_guest(
    guest_id: uuid.UUID, 
    card_assign: schemas.CardAssign, 
    db: Session = Depends(get_db),
    # --- ИЗМЕНЕНИЕ: Явно запрашиваем текущего пользователя. ---
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    db_guest = guest_crud.get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    db_card = card_crud.get_card_by_uid(db, uid=card_assign.card_uid)

    if db_card:
        if db_card.guest_id and db_card.guest_id != guest_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Card with UID {card_assign.card_uid} is already assigned to another guest."
            )
        card_crud.assign_card_to_guest(db, db_card=db_card, guest_id=guest_id)
    else:
        new_card_schema = schemas.CardCreate(card_uid=card_assign.card_uid)
        card_crud.create_and_assign_card(db, card=new_card_schema, guest_id=guest_id)

    db.refresh(db_guest)
    return db_guest

@router.delete("/{guest_id}/cards/{card_uid}", response_model=schemas.Guest, summary="Отвязать карту от гостя")
def unassign_card_from_guest(
    guest_id: uuid.UUID, 
    card_uid: str, 
    db: Session = Depends(get_db),
    # --- ИЗМЕНЕНИЕ: Явно запрашиваем текущего пользователя. ---
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    return guest_crud.unassign_card_from_guest(db=db, guest_id=guest_id, card_uid=card_uid)

@router.post("/{guest_id}/topup", response_model=schemas.Guest, summary="Пополнить баланс гостя")
def topup_guest_balance(
    guest_id: uuid.UUID, 
    topup_data: schemas.TopUpRequest, 
    db: Session = Depends(get_db),
    # --- ИЗМЕНЕНИЕ: Явно запрашиваем текущего пользователя. ---
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    return transaction_crud.create_topup_transaction(db=db, guest_id=guest_id, topup_data=topup_data)

@router.get("/{guest_id}/history", response_model=schemas.GuestHistoryResponse, summary="Получить историю операций гостя")
def get_guest_history(
    guest_id: uuid.UUID, 
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None
):
    return guest_crud.get_guest_history(
        db=db, guest_id=guest_id, start_date=start_date, end_date=end_date
    )