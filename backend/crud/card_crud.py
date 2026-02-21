# backend/crud/card_crud.py
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
import models
import schemas
import uuid

def create_card(db: Session, card: schemas.CardCreate):
    """Регистрирует новую RFID-карту в системе."""
    # КОММЕНТАРИЙ: Эта функция остается для ручного администрирования,
    # но не используется в основном сценарии привязки карты гостю.
    db_card_by_uid = db.query(models.Card).filter(models.Card.card_uid == card.card_uid).first()
    if db_card_by_uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card with UID {card.card_uid} already registered."
        )
    
    # КОММЕНТАРИЙ: Здесь возникает ошибка NotNullViolation, если guest_id обязателен в БД.
    # Мы не будем использовать эту функцию для привязки.
    db_card = models.Card(card_uid=card.card_uid, status="inactive")
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def get_card_by_uid(db: Session, uid: str):
    """Находит карту по ее уникальному идентификатору (card_uid)."""
    return db.query(models.Card).filter(models.Card.card_uid == uid).first()

def get_cards(db: Session, skip: int = 0, limit: int = 100):
    """Возвращает список всех карт с информацией о привязанных гостях."""
    return db.query(models.Card).options(
        joinedload(models.Card.guest)
    ).order_by(models.Card.created_at.desc()).offset(skip).limit(limit).all()

def update_card_status(db: Session, card_uid: str, new_status: str):
    """Обновляет статус карты (например, 'lost'), находя ее по UID."""
    db_card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if not db_card:
        return None
    
    db_card.status = new_status
    db.commit()
    db.refresh(db_card)
    return db_card

# +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем недостающие CRUD-функции +++

def assign_card_to_guest(db: Session, db_card: models.Card, guest_id: uuid.UUID):
    """
    Привязывает существующий объект карты к гостю и активирует ее.
    """
    db_card.guest_id = guest_id
    # Card is operationally activated by opening a Visit (M2).
    db_card.status = "inactive"
    db.commit()
    db.refresh(db_card)
    return db_card

def create_and_assign_card(db: Session, card: schemas.CardCreate, guest_id: uuid.UUID):
    """
    Создает новую карту и сразу же привязывает ее к гостю.
    Это решает проблему NotNullViolation.
    """
    # Создаем объект модели, передавая все необходимые поля сразу.
    db_card = models.Card(
        card_uid=card.card_uid, 
        guest_id=guest_id,
        # Card is operationally activated by opening a Visit (M2).
        status="inactive"
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

# +++ КОНЕЦ ИЗМЕНЕНИЙ +++