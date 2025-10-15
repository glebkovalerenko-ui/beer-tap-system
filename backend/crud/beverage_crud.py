from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import models, schemas

def get_beverage(db: Session, beverage_id: int):
    """ Получение одного напитка по ID. """
    db_beverage = db.query(models.Beverage).filter(models.Beverage.beverage_id == beverage_id).first()
    if db_beverage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beverage not found")
    return db_beverage

def get_beverage_by_name(db: Session, name: str):
    """ Получение напитка по его точному названию. """
    return db.query(models.Beverage).filter(models.Beverage.name == name).first()

def get_beverages(db: Session, skip: int = 0, limit: int = 100):
    """ Получение списка напитков с пагинацией. """
    return db.query(models.Beverage).offset(skip).limit(limit).all()
    
def create_beverage(db: Session, beverage: schemas.BeverageCreate):
    """ Создание нового напитка в справочнике. """
    # Проверяем, не существует ли уже напиток с таким названием
    if get_beverage_by_name(db, name=beverage.name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Beverage with this name already exists")
        
    # Создаем экземпляр модели SQLAlchemy из Pydantic схемы
    db_beverage = models.Beverage(**beverage.model_dump())
    
    db.add(db_beverage)
    db.commit()
    db.refresh(db_beverage)
    return db_beverage