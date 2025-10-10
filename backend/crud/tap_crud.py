# backend/crud/tap_crud.py
from sqlalchemy.orm import Session
import models

def get_tap_by_id(db: Session, tap_id: int):
    return db.query(models.Tap).filter(models.Tap.tap_id == tap_id).first()