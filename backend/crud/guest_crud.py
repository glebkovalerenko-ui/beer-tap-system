# backend/crud/guest_crud.py
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from typing import Optional 
from datetime import date
import models
import schemas
from crud import card_crud
import uuid

# --- READ операции ---

def get_guest(db: Session, guest_id: uuid.UUID):
    """Получить одного гостя по его UUID с предварительной загрузкой его карт."""
    return db.query(models.Guest).options(
        joinedload(models.Guest.cards)
    ).filter(models.Guest.guest_id == guest_id).first()

def get_guests(db: Session, skip: int = 0, limit: int = 100):
    """Получить список гостей с пагинацией и с предварительной загрузкой их карт."""
    return db.query(models.Guest).options(
        joinedload(models.Guest.cards)
    ).order_by(models.Guest.last_name).offset(skip).limit(limit).all()

# --- CREATE операция ---
def create_guest(db: Session, guest: schemas.GuestCreate):
    """Создать нового гостя."""
    db_guest = models.Guest(**guest.model_dump())
    # ... (остальной код create_guest без изменений)
    db_guest_by_doc = db.query(models.Guest).filter(models.Guest.id_document == guest.id_document).first()
    if db_guest_by_doc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail="Guest with this ID document already registered")
    db_guest_by_phone = db.query(models.Guest).filter(models.Guest.phone_number == guest.phone_number).first()
    if db_guest_by_phone:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                            detail="Guest with this phone number already registered")
    db.add(db_guest)
    db.commit()
    db.refresh(db_guest)
    return db_guest

# --- УПРАВЛЕНИЕ КАРТАМИ ГОСТЯ ---

def assign_card_to_guest(db: Session, guest_id: uuid.UUID, uid: str):
    """Привязывает существующую, незанятую карту к гостю."""
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")

    db_card = card_crud.get_card_by_uid(db, uid=uid)
    if not db_card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Card with UID {uid} not found. Register it first.")

    if db_card.guest_id is not None:
        if db_card.guest_id == guest_id:
            return db_guest
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is already assigned to another guest")
            
    db_card.guest_id = guest_id
    db_card.status = "active"
    db.commit()
    db.refresh(db_guest)
    return db_guest

def unassign_card_from_guest(db: Session, guest_id: uuid.UUID, card_uid: str):
    """Отвязывает карту от гостя, делая ее неактивной."""
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
            
    ## ИЗМЕНЕНО: Находим карту по card_uid, а не по несуществующему card_id
    db_card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if not db_card or db_card.guest_id != guest_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found or not assigned to this guest")
            
    db_card.guest_id = None
    db_card.status = "inactive"
    db.commit()
    db.refresh(db_guest)
    return db_guest

def get_guest_history(db: Session, guest_id: uuid.UUID, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """
    Собирает, унифицирует и сортирует полную историю операций гостя.
    """
    # 1. Проверяем, существует ли гость.
    db_guest = get_guest(db, guest_id=guest_id)
    if not db_guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found")
        
    history_items = []

    # 2. Получаем финансовые транзакции (пополнения, возвраты).
    transactions_query = db.query(models.Transaction).filter(models.Transaction.guest_id == guest_id)
    if start_date:
        transactions_query = transactions_query.filter(models.Transaction.created_at >= start_date)
    if end_date:
        transactions_query = transactions_query.filter(models.Transaction.created_at <= end_date)
    
    for tx in transactions_query.all():
        history_items.append(schemas.HistoryItem(
            timestamp=tx.created_at,
            type=tx.type,
            amount=tx.amount, # Сумма уже положительная
            details=f"Пополнение: {tx.payment_method}"
        ))

    # 3. Получаем наливы (списания).
    pours_query = db.query(models.Pour).filter(models.Pour.guest_id == guest_id).options(
        # "Жадно" загружаем связанные данные, чтобы избежать N+1 запросов
        joinedload(models.Pour.keg).joinedload(models.Keg.beverage)
    )
    if start_date:
        pours_query = pours_query.filter(models.Pour.poured_at >= start_date)
    if end_date:
        pours_query = pours_query.filter(models.Pour.poured_at <= end_date)

    for pour in pours_query.all():
        beverage_name = pour.keg.beverage.name if pour.keg and pour.keg.beverage else "Unknown Beverage"
        history_items.append(schemas.HistoryItem(
            timestamp=pour.poured_at,
            type="pour",
            amount=-pour.amount_charged, # ВАЖНО: делаем сумму отрицательной для списаний
            details=f"Налив: {beverage_name} {pour.volume_ml} мл"
        ))
        
    # 4. Сортируем объединенный список по времени в обратном порядке (самые новые - сначала).
    history_items.sort(key=lambda item: item.timestamp, reverse=True)
    
    return schemas.GuestHistoryResponse(guest_id=guest_id, history=history_items)