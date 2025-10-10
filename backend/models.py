# backend/models.py
# Импортируем все необходимые типы данных
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, 
    Boolean, ForeignKey, text
)
from sqlalchemy.sql import func
from sqlalchemy.types import DECIMAL 
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Импортируем UUID и переименовываем
from database import Base

# --- МОДЕЛЬ GUEST (Уже исправлена и соответствует схеме) ---
class Guest(Base):
    __tablename__ = "guests"

    guest_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    last_name = Column(String(50), nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    patronymic = Column(String(50), nullable=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    id_document = Column(String(100), unique=True, nullable=False, index=True)
    balance = Column(DECIMAL(10, 2), nullable=False, server_default=text("0.00"))
    is_active = Column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# --- НОВЫЕ МОДЕЛИ: Добавляем недостающие определения ---

class Card(Base):
    __tablename__ = "cards"
    card_uid = Column(String(50), primary_key=True)
    guest_id = Column(PG_UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=False)
    status = Column(String(20), nullable=False, server_default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Keg(Base):
    __tablename__ = "kegs"
    keg_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    beer_name = Column(String(100), nullable=False)
    brewery = Column(String(100))
    beer_style = Column(String(50))
    abv = Column(DECIMAL(4, 2))
    initial_volume_ml = Column(Integer, nullable=False)
    current_volume_ml = Column(Integer, nullable=False)
    purchase_price = Column(DECIMAL(10, 2))
    tapped_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Tap(Base):
    __tablename__ = "taps"
    tap_id = Column(Integer, primary_key=True) # SERIAL в SQL -> Integer + primary_key в SQLAlchemy
    keg_id = Column(PG_UUID(as_uuid=True), ForeignKey("kegs.keg_id"), nullable=True)
    display_name = Column(String(50), nullable=False)
    price_per_ml = Column(DECIMAL(10, 4), nullable=False)
    last_cleaned_at = Column(DateTime(timezone=True))

# --- МОДЕЛЬ POUR (Уже исправлена и соответствует схеме) ---
class Pour(Base):
    __tablename__ = "pours"

    pour_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Внешние ключи
    guest_id = Column(PG_UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=False)
    card_uid = Column(String, ForeignKey("cards.card_uid"), nullable=False)
    tap_id = Column(Integer, ForeignKey("taps.tap_id"), nullable=False)
    keg_id = Column(PG_UUID(as_uuid=True), ForeignKey("kegs.keg_id"), nullable=False)
    
    # Детали транзакции
    client_tx_id = Column(String(100), unique=True, nullable=False, index=True)
    volume_ml = Column(Integer, nullable=False)
    price_per_ml_at_pour = Column(DECIMAL(10, 4), nullable=False)
    amount_charged = Column(DECIMAL(10, 2), nullable=False)
    
    # Временные метки
    poured_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())