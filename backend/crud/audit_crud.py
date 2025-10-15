# backend/crud/audit_crud.py
from sqlalchemy.orm import Session
import models
import json
from typing import Optional

def create_audit_log(
    db: Session,
    *,
    actor_id: str,
    action: str,
    target_entity: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None
):
    """
    Создает новую запись в журнале аудита.
    ВАЖНО: Эта функция НЕ делает commit. Commit должен управляться вызывающей функцией.
    """
    
    details_str = json.dumps(details, ensure_ascii=False) if details else None

    db_log = models.AuditLog(
        actor_id=actor_id,
        action=action,
        target_entity=target_entity,
        target_id=target_id,
        details=details_str
    )
    db.add(db_log)
    # db.flush() # Можно использовать, если нужно получить ID лога сразу, но здесь не требуется
    return