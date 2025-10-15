# backend/crud/audit_crud.py
from sqlalchemy.orm import Session
import models
import json # Импортируем для работы с JSON

def create_audit_log(
    db: Session,
    actor_id: str,
    action: str,
    target_entity: str = None,
    target_id: str = None,
    details: dict = None # Принимаем словарь для удобства
):
    """Создает новую запись в журнале аудита."""
    
    # Конвертируем словарь деталей в строку JSON, если он предоставлен
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
    # db.refresh не нужен, мы не возвращаем объект
    return