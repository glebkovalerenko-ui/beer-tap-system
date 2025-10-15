# backend/crud/system_crud.py
from sqlalchemy.orm import Session
import models
import schemas

def get_all_states(db: Session) -> list[models.SystemState]:
    """Возвращает все записи о состоянии системы."""
    return db.query(models.SystemState).all()

def get_state(db: Session, key: str, default: str = "false") -> models.SystemState:
    """
    Возвращает значение конкретного флага.
    Если флаг не найден, создает его со значением по умолчанию.
    """
    db_state = db.query(models.SystemState).filter(models.SystemState.key == key).first()
    if not db_state:
        # Создаем запись, если она не существует
        db_state = models.SystemState(key=key, value=default)
        db.add(db_state)
        db.commit()
        db.refresh(db_state)
    return db_state

def set_state(db: Session, key: str, value: str) -> models.SystemState:
    """
    Устанавливает (обновляет или создает) значение для конкретного флага.
    Реализует логику "upsert".
    """
    db_state = db.query(models.SystemState).filter(models.SystemState.key == key).first()
    if db_state:
        # Обновляем, если существует
        db_state.value = value
    else:
        # Создаем, если не существует
        db_state = models.SystemState(key=key, value=value)
        db.add(db_state)
    
    db.commit()
    db.refresh(db_state)
    return db_state