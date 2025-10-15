# backend/crud/card_crud.py
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
import models
import schemas
import uuid

def create_card(db: Session, card: schemas.CardCreate):
    """Регистрирует новую RFID-карту в системе."""
    ## ИЗМЕНЕНО: Используем card_uid из схемы и модели
    db_card_by_uid = db.query(models.Card).filter(models.Card.card_uid == card.card_uid).first()
    if db_card_by_uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card with UID {card.card_uid} already registered."
        )
    
    db_card = models.Card(card_uid=card.card_uid, status="inactive")
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def get_card_by_uid(db: Session, uid: str):
    """Находит карту по ее уникальному идентификатору (card_uid)."""
    ## ИЗМЕНЕНО: Используем card_uid для поиска
    return db.query(models.Card).filter(models.Card.card_uid == uid).first()

def get_cards(db: Session, skip: int = 0, limit: int = 100):
    """Возвращает список всех карт с информацией о привязанных гостях."""
    return db.query(models.Card).options(
        joinedload(models.Card.guest)
    ).order_by(models.Card.created_at.desc()).offset(skip).limit(limit).all()

def update_card_status(db: Session, card_uid: str, new_status: str):
    """Обновляет статус карты (например, 'lost'), находя ее по UID."""
    ## ИЗМЕНЕНО: ID карты - это ее UID (string), а не число.
    db_card = db.query(models.Card).filter(models.Card.card_uid == card_uid).first()
    if not db_card:
        return None
    
    db_card.status = new_status
    db.commit()
    db.refresh(db_card)
    return db_card