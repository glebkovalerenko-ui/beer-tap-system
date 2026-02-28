# backend/crud/system_crud.py
from sqlalchemy.orm import Session

import models
import schemas


MIN_START_ML_KEY = "min_start_ml"
SAFETY_ML_KEY = "safety_ml"
ALLOWED_OVERDRAFT_CENTS_KEY = "allowed_overdraft_cents"

DEFAULT_MIN_START_ML = 20
DEFAULT_SAFETY_ML = 2
DEFAULT_ALLOWED_OVERDRAFT_CENTS = 0

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


def get_int_state(db: Session, key: str, default: int, *, minimum: int = 0) -> int:
    state = get_state(db=db, key=key, default=str(default))
    try:
        parsed = int(str(state.value).strip())
    except (TypeError, ValueError):
        parsed = default

    if parsed < minimum:
        parsed = minimum

    if str(state.value) != str(parsed):
        state.value = str(parsed)
        db.commit()
        db.refresh(state)

    return parsed


def get_pour_policy(db: Session) -> dict[str, int]:
    return {
        "min_start_ml": get_int_state(db, MIN_START_ML_KEY, DEFAULT_MIN_START_ML, minimum=1),
        "safety_ml": get_int_state(db, SAFETY_ML_KEY, DEFAULT_SAFETY_ML, minimum=0),
        "allowed_overdraft_cents": get_int_state(
            db,
            ALLOWED_OVERDRAFT_CENTS_KEY,
            DEFAULT_ALLOWED_OVERDRAFT_CENTS,
            minimum=0,
        ),
    }
