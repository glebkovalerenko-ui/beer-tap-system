# backend/crud/keg_crud.py
import uuid
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
import models, schemas
from crud import beverage_crud

def get_keg(db: Session, keg_id: uuid.UUID):
    """ Получение одной кеги по ее UUID. """
    db_keg = db.query(models.Keg).options(
        joinedload(models.Keg.beverage)
    ).filter(models.Keg.keg_id == keg_id).first()
    
    if db_keg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keg not found")
    return db_keg

def get_kegs(db: Session, skip: int = 0, limit: int = 100):
    """ Получение списка всех кег. """
    return db.query(models.Keg).options(
        joinedload(models.Keg.beverage)
    ).offset(skip).limit(limit).all()

def create_keg(db: Session, keg: schemas.KegCreate):
    """ Создание новой кеги в системе. """
    # --- Бизнес-логика 1: Проверяем, существует ли напиток, который мы заливаем в кегу ---
    beverage_crud.get_beverage(db, beverage_id=keg.beverage_id)

    # --- Бизнес-логика 2: При создании, текущий объем равен начальному ---
    db_keg = models.Keg(
        beverage_id=keg.beverage_id,
        initial_volume_ml=keg.initial_volume_ml,
        purchase_price=keg.purchase_price,
        current_volume_ml=keg.initial_volume_ml # Устанавливаем текущий объем
    )
    
    db.add(db_keg)
    db.commit()
    db.refresh(db_keg)
    return db_keg

def update_keg(db: Session, keg_id: uuid.UUID, keg_update: schemas.KegUpdate):
    """ Обновление данных кеги (сейчас только статус). """
    db_keg = get_keg(db, keg_id=keg_id)
    
    update_data = keg_update.model_dump(exclude_unset=True)
    
    # --- Бизнес-логика 3: Автоматически устанавливаем временные метки при смене статуса ---
    if 'status' in update_data:
        new_status = update_data['status']
        if new_status == 'in_use' and db_keg.tapped_at is None:
            db_keg.tapped_at = func.now()
        elif new_status == 'empty' and db_keg.finished_at is None:
            db_keg.finished_at = func.now()

    for key, value in update_data.items():
        setattr(db_keg, key, value)
    db.commit()
    db.refresh(db_keg)
    return db_keg

def delete_keg(db: Session, keg_id: uuid.UUID):
    """ Удаление кеги из системы. """
    db_keg = get_keg(db, keg_id=keg_id)

    # --- ИЗМЕНЕНИЕ: Реализована проверка бизнес-правила ---
    # Нельзя удалить кегу, которая в данный момент подключена к крану.
    if db_keg.status == 'in_use':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete keg {keg_id} because it is currently in use."
        )
        
    db.delete(db_keg)
    db.commit()
    
    # Для операции DELETE мы не возвращаем тело ответа,
    # поэтому возвращать объект не обязательно.
    return db_keg
