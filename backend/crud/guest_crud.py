# backend/crud/guest_crud.py
from sqlalchemy.orm import Session
import models, schemas
import uuid

# --- READ операции ---

def get_guest(db: Session, guest_id: uuid.UUID):
    """Получить гостя по его UUID."""
    return db.query(models.Guest).filter(models.Guest.guest_id == guest_id).first()

def get_guest_by_phone(db: Session, phone_number: str):
    """Получить гостя по номеру телефона."""
    return db.query(models.Guest).filter(models.Guest.phone_number == phone_number).first()

def get_guest_by_document(db: Session, id_document: str):
    """Получить гостя по номеру документа."""
    return db.query(models.Guest).filter(models.Guest.id_document == id_document).first()

def get_guests(db: Session, skip: int = 0, limit: int = 100):
    """Получить список гостей с пагинацией."""
    return db.query(models.Guest).offset(skip).limit(limit).all()

# --- CREATE операция ---

def create_guest(db: Session, guest: schemas.GuestCreate):
    """Создать нового гостя."""
    # Преобразуем Pydantic схему в словарь и создаем на его основе
    # объект модели SQLAlchemy
    db_guest = models.Guest(**guest.dict())
    
    # Добавляем объект в сессию (готовим к сохранению)
    db.add(db_guest)
    # Сохраняем изменения в базе данных
    db.commit()
    # Обновляем объект, чтобы получить данные, сгенерированные БД (например, guest_id)
    db.refresh(db_guest)
    
    return db_guest