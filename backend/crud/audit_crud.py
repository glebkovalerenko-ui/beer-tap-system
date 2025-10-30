# backend/crud/audit_crud.py

from sqlalchemy.orm import Session
import models
import json
from typing import Optional
import logging # <-- ИЗМЕНЕНИЕ: Импортируем logging

# --- ИЗМЕНЕНИЕ: Получаем экземпляр логгера ---
logger = logging.getLogger(__name__)

def create_audit_log_entry(
    db: Session,
    *,
    actor_id: str,
    action: str,
    target_entity: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    Создает новую запись в журнале аудита и коммитит ее.
    Предназначена для вызова в фоновых задачах.
    """
    try:
        details_str = json.dumps(details, ensure_ascii=False) if details else None

        db_log = models.AuditLog(
            actor_id=actor_id,
            action=action,
            target_entity=target_entity,
            target_id=target_id,
            details=details_str
        )
        db.add(db_log)
        db.commit()
        # --- ИЗМЕНЕНИЕ: print() заменен на logger.info() ---
        logger.info(f"Фоновая запись в лог аудита успешно завершена для действия: {action}")

    except Exception as e:
        # --- ИЗМЕНЕНИЕ: print() заменен на logger.error() ---
        logger.error(f"Ошибка в фоновой задаче аудита: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()