# backend/schemas.py
import uuid
from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal # Импортируем Decimal для валидации

# --- Схемы для Гостей (Guests) ---

# Базовая схема - данные, которые предоставляет пользователь при регистрации
class GuestBase(BaseModel):
    last_name: str = Field(..., example="Иванов")
    first_name: str = Field(..., example="Иван")
    patronymic: str | None = Field(default=None, example="Иванович")
    phone_number: str = Field(..., example="+79211234567")
    date_of_birth: date = Field(..., example="1990-01-15")
    id_document: str = Field(..., example="4510 123456")

# Схема для создания (наследуется от базовой)
class GuestCreate(GuestBase):
    pass

# Схема для отображения - данные, которые мы возвращаем из API
class Guest(GuestBase):
    # Поля, которые генерируются сервером/БД и отдаются клиенту
    guest_id: uuid.UUID = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    balance: Decimal = Field(..., example="150.75")
    is_active: bool = Field(..., example=True)
    created_at: datetime = Field(..., example="2025-10-08T12:00:00.000Z")
    updated_at: datetime = Field(..., example="2025-10-08T12:05:10.000Z")

    class Config:
        from_attributes = True

# Схема для одной транзакции налива, приходящей от контроллера
# Приводим ее в соответствие с тем, что шлет sync_client.py
class PourData(BaseModel):
    client_tx_id: str # Контроллер шлет строку, а не UUID
    card_uid: str
    tap_id: int
    start_ts: datetime # Это poured_at в нашей новой модели
    end_ts: datetime # Это поле мы пока просто принимаем, но не сохраняем
    volume_ml: int
    price_cents: int # Это amount_charged в нашей новой модели

# Схема для всего запроса синхронизации (пачки транзакций)
class SyncRequest(BaseModel):
    pours: list[PourData]

# Схема для ответа сервера на одну транзакцию
class SyncResult(BaseModel):
    client_tx_id: str # Отвечаем тоже строкой
    status: str # 'accepted' или 'rejected'
    reason: str | None = None

# Схема для всего ответа сервера
class SyncResponse(BaseModel):
    results: list[SyncResult]