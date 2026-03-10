import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

import schemas
import security
from crud import keg_crud
from database import get_db


router = APIRouter(
    prefix="/kegs",
    tags=["Kegs"],
    dependencies=[Depends(security.get_current_user)],
)


@router.post("/", response_model=schemas.Keg, status_code=201, summary="Зарегистрировать новую кегу")
def create_keg(keg: schemas.KegCreate, db: Session = Depends(get_db)):
    return keg_crud.create_keg(db=db, keg=keg)


@router.get("/suggest", response_model=schemas.KegSuggestionResponse, summary="Получить FIFO-рекомендацию кеги по типу пива")
def suggest_keg(
    beer_type_id: uuid.UUID = Query(..., description="UUID beer type; in current schema maps to beverage_id"),
    db: Session = Depends(get_db),
):
    return keg_crud.get_fifo_suggestion(db=db, beer_type_id=beer_type_id)


@router.get("/", response_model=List[schemas.Keg], summary="Получить список всех кег")
def read_kegs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return keg_crud.get_kegs(db, skip=skip, limit=limit)


@router.get("/{keg_id}", response_model=schemas.Keg, summary="Получить кегу по ID")
def read_keg(keg_id: uuid.UUID, db: Session = Depends(get_db)):
    return keg_crud.get_keg(db, keg_id=keg_id)


@router.put("/{keg_id}", response_model=schemas.Keg, summary="Обновить статус кеги")
def update_keg(keg_id: uuid.UUID, keg_update: schemas.KegUpdate, db: Session = Depends(get_db)):
    return keg_crud.update_keg(db=db, keg_id=keg_id, keg_update=keg_update)


@router.delete(
    "/{keg_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить кегу",
    responses={
        409: {"description": "Cannot delete a keg that is currently in use"},
        404: {"description": "Keg not found"},
    },
)
def delete_keg(keg_id: uuid.UUID, db: Session = Depends(get_db)):
    keg_crud.delete_keg(db=db, keg_id=keg_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
