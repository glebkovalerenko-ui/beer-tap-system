# backend/api/audit.py
from typing import List, Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Абсолютные импорты
import schemas
import security
import models
from database import get_db


router = APIRouter(
    prefix="/api/audit",
    tags=["Audit"]
)

@router.get("/", response_model=List[schemas.AuditLog], summary="Получить журнал аудита")
def read_audit_logs(
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)],
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Возвращает список последних записей из журнала аудита в обратном хронологическом порядке.

    Этот эндпоинт позволяет администраторам отслеживать все важные, изменяющие состояние
    действия, совершенные в системе.
    """
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs