# backend/api/pours.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import schemas
import security
from crud import pour_crud
from database import get_db

router = APIRouter(
    prefix="/pours",
    tags=["Pours"],
    dependencies=[Depends(security.get_current_user)]
)

@router.get("/", response_model=List[schemas.PourResponse], summary="Получить список последних наливов")
def read_pours(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """
    Возвращает список последних транзакций по наливам для отображения
    на дашборде и в истории.
    """
    return pour_crud.get_pours(db, skip=skip, limit=limit)