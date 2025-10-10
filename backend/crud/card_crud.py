# backend/crud/card_crud.py
from sqlalchemy.orm import Session
import models

def get_card_by_uid(db: Session, card_uid: str):
    return db.query(models.Card).filter(models.Card.card_uid == card_uid).first()