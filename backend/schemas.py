# backend/schemas.py
import uuid
# --- ИЗМЕНЕНИЕ: Добавлен импорт ConfigDict для современного синтаксиса Pydantic v2 ---
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

# =============================================================================
# СХЕМЫ ДЛЯ БИЗНЕС-ЛОГИКИ
# =============================================================================

# --- Схемы для Напитков (Beverage) ---
class BeverageBase(BaseModel):
    # --- ИЗМЕНЕНИЕ: 'example' заменен на 'json_schema_extra' ---
    name: str = Field(..., json_schema_extra={'example': "Guinness"})
    brewery: Optional[str] = Field(default=None, json_schema_extra={'example': "St. James's Gate Brewery"})
    style: Optional[str] = Field(default=None, json_schema_extra={'example': "Stout"})
    abv: Optional[Decimal] = Field(default=None, json_schema_extra={'example': 4.2})
    sell_price_per_liter: Decimal = Field(..., json_schema_extra={'example': 700.00})

class BeverageCreate(BeverageBase):
    pass

class Beverage(BeverageBase):
    beverage_id: uuid.UUID
    # --- ИЗМЕНЕНИЕ: 'class Config' заменен на 'model_config' ---
    model_config = ConfigDict(from_attributes=True)

# --- Схемы для Кег (Keg) ---
class KegBase(BaseModel):
    initial_volume_ml: int = Field(..., json_schema_extra={'example': 50000})
    purchase_price: Decimal = Field(..., json_schema_extra={'example': 10000.00})

class KegCreate(KegBase):
    beverage_id: uuid.UUID

class KegUpdate(BaseModel):
    status: Optional[str] = Field(default=None, json_schema_extra={'example': "empty"})

class Keg(KegBase):
    keg_id: uuid.UUID
    beverage_id: uuid.UUID
    current_volume_ml: int
    status: str
    tapped_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    beverage: Beverage
    model_config = ConfigDict(from_attributes=True)

# --- Схемы для Кранов (Tap) ---
class TapBase(BaseModel):
    display_name: str = Field(..., json_schema_extra={'example': "Кран №1"})

class TapCreate(TapBase):
    pass

class TapUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None

class TapAssignKeg(BaseModel):
    keg_id: uuid.UUID

class Tap(TapBase):
    tap_id: int
    status: str
    keg_id: Optional[uuid.UUID] = None
    keg: Optional[Keg] = None
    model_config = ConfigDict(from_attributes=True)

# --- Схемы для Карт (Card) ---
class CardCreate(BaseModel):
    card_uid: str = Field(..., json_schema_extra={'example': "04AB7815CD6B80"})

class Card(BaseModel):
    card_uid: str
    guest_id: Optional[uuid.UUID] = None
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CardAssign(BaseModel):
    card_uid: str = Field(..., json_schema_extra={'example': "04AB7815CD6B80"})

class CardStatusUpdate(BaseModel):
    status: str = Field(..., json_schema_extra={'example': "lost"})


class VisitOpenRequest(BaseModel):
    guest_id: uuid.UUID
    card_uid: Optional[str] = Field(default=None, json_schema_extra={'example': "04AB7815CD6B80"})


class VisitCloseRequest(BaseModel):
    closed_reason: str = Field(..., min_length=1, json_schema_extra={'example': "guest_checkout"})
    card_returned: bool = Field(default=True)


class Visit(BaseModel):
    visit_id: uuid.UUID
    guest_id: uuid.UUID
    card_uid: Optional[str]
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    closed_reason: Optional[str] = None
    active_tap_id: Optional[int] = None
    lock_set_at: Optional[datetime] = None
    card_returned: bool
    model_config = ConfigDict(from_attributes=True)




class VisitAssignCardRequest(BaseModel):
    card_uid: str = Field(..., min_length=1, json_schema_extra={'example': "04AB7815CD6B80"})


class VisitActiveListItem(BaseModel):
    visit_id: uuid.UUID
    guest_id: uuid.UUID
    guest_full_name: str
    phone_number: str
    balance: Decimal
    status: str
    card_uid: Optional[str] = None
    active_tap_id: Optional[int] = None
    lock_set_at: Optional[datetime] = None
    opened_at: datetime

class VisitPourAuthorizeRequest(BaseModel):
    card_uid: str = Field(..., json_schema_extra={'example': "04AB7815CD6B80"})
    tap_id: int = Field(..., ge=1, json_schema_extra={'example': 1})


class VisitPourAuthorizeResponse(BaseModel):
    allowed: bool
    visit: Optional[Visit] = None
    reason: Optional[str] = None


class VisitForceUnlockRequest(BaseModel):
    reason: str = Field(..., min_length=1, json_schema_extra={'example': "controller_offline_recovery"})
    comment: Optional[str] = Field(default=None, json_schema_extra={'example': "Manual unlock after timeout"})


class VisitReconcilePourRequest(BaseModel):
    tap_id: int = Field(..., ge=1, json_schema_extra={'example': 1})
    short_id: str = Field(..., min_length=6, max_length=8, json_schema_extra={'example': "A1B2C3"})
    volume_ml: int = Field(..., ge=1, json_schema_extra={'example': 250})
    amount: Decimal = Field(..., gt=0, json_schema_extra={'example': 175.00})
    reason: str = Field(..., min_length=1, json_schema_extra={'example': "sync_timeout"})
    comment: Optional[str] = Field(default=None, json_schema_extra={'example': "Operator entered from controller screen"})

class TopUpRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, json_schema_extra={'example': 500.00}, description="Сумма пополнения, должна быть больше нуля")
    payment_method: str = Field(..., json_schema_extra={'example': "cash"}, description="Метод оплаты (e.g., 'cash', 'card')")

class HistoryItem(BaseModel):
    timestamp: datetime
    type: str = Field(..., json_schema_extra={'example': "pour | top-up"})
    amount: Decimal = Field(..., description="Положительное для пополнений, отрицательное для наливов")
    details: str = Field(..., json_schema_extra={'example': "Налив: Guinness 500 мл | Пополнение: Наличные"})

class GuestHistoryResponse(BaseModel):
    guest_id: uuid.UUID
    history: List[HistoryItem] = []

# --- Схемы для Финансовых Транзакций (Transaction) ---
class TransactionBase(BaseModel):
    amount: Decimal
    type: str = Field(..., json_schema_extra={'example': "top-up"})
    payment_method: Optional[str] = Field(default=None, json_schema_extra={'example': "cash"})

class TransactionCreate(TransactionBase):
    guest_id: uuid.UUID
    visit_id: Optional[uuid.UUID] = None

class Transaction(TransactionBase):
    transaction_id: uuid.UUID
    guest_id: uuid.UUID
    visit_id: Optional[uuid.UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
        
# --- Схемы для Наливов (Pour) ---
class Pour(BaseModel):
    pour_id: uuid.UUID
    volume_ml: int
    amount_charged: Decimal
    sync_status: str
    short_id: Optional[str] = None
    is_manual_reconcile: bool = False
    poured_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Компактная схема для отображения гостя в ленте наливов ---
class PourGuest(BaseModel):
    guest_id: uuid.UUID
    last_name: str
    first_name: str
    model_config = ConfigDict(from_attributes=True)

# --- Расширенная схема налива для ответа API. Включает в себя вложенные данные о госте и напитке для удобства фронтенда. ---
class PourResponse(Pour):
    guest: PourGuest
    beverage: Beverage # Мы можем переиспользовать уже существующую схему Beverage
    tap: Tap # И схему Tap
    model_config = ConfigDict(from_attributes=True)
        
# --- Схемы для Гостей (Guests) ---
class GuestBase(BaseModel):
    last_name: str = Field(..., json_schema_extra={'example': "Иванов"})
    first_name: str = Field(..., json_schema_extra={'example': "Иван"})
    patronymic: Optional[str] = Field(default=None, json_schema_extra={'example': "Иванович"})
    phone_number: str = Field(..., json_schema_extra={'example': "+79211234567"})
    date_of_birth: date = Field(..., json_schema_extra={'example': "1990-01-15"})
    id_document: str = Field(..., json_schema_extra={'example': "4510 123456"})

class GuestCreate(GuestBase):
    pass

class GuestUpdate(BaseModel):
    """
    Схема для обновления данных гостя. Все поля опциональны,
    чтобы клиент мог отправлять только измененные данные.
    """
    last_name: Optional[str] = Field(default=None, json_schema_extra={'example': "Петров"})
    first_name: Optional[str] = Field(default=None, json_schema_extra={'example': "Петр"})
    patronymic: Optional[str] = Field(default=None, json_schema_extra={'example': "Петрович"})
    phone_number: Optional[str] = Field(default=None, json_schema_extra={'example': "+79217654321"})
    date_of_birth: Optional[date] = Field(default=None, json_schema_extra={'example': "1991-02-16"})
    id_document: Optional[str] = Field(default=None, json_schema_extra={'example': "4511 654321"})
    is_active: Optional[bool] = Field(default=None, json_schema_extra={'example': False})

class Guest(GuestBase):
    guest_id: uuid.UUID
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    cards: List[Card] = []
    transactions: List[Transaction] = []
    pours: List[Pour] = []
    model_config = ConfigDict(from_attributes=True)

# --- Схемы для Синхронизации с Контроллером ---
class PourData(BaseModel):
    client_tx_id: str
    card_uid: str
    tap_id: int
    short_id: str = Field(..., min_length=6, max_length=8)
    start_ts: datetime
    end_ts: datetime
    volume_ml: int
    price_cents: int

class SyncRequest(BaseModel):
    pours: list[PourData]

class SyncResult(BaseModel):
    client_tx_id: str
    status: str
    reason: Optional[str] = None

class SyncResponse(BaseModel):
    results: list[SyncResult]

# =============================================================================
# СИСТЕМНЫЕ СХЕМЫ
# =============================================================================

# --- Схемы для Контроллеров (Controller) ---
class ControllerRegister(BaseModel):
    controller_id: str = Field(..., json_schema_extra={'example': "00:1A:2B:3C:4D:5E"}, description="Уникальный ID контроллера, e.g., MAC-адрес")
    ip_address: str = Field(..., json_schema_extra={'example': "192.168.1.101"}, description="Текущий IP-адрес контроллера в сети")
    firmware_version: Optional[str] = Field(default=None, json_schema_extra={'example': "1.0.2"}, description="Версия прошивки на устройстве")

class Controller(BaseModel):
    controller_id: str
    ip_address: str
    firmware_version: Optional[str] = None
    created_at: datetime
    last_seen: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Схемы для Глобального Состояния Системы ---
class SystemStateItem(BaseModel):
    key: str
    value: str

class SystemStateUpdate(BaseModel):
    value: str = Field(..., json_schema_extra={'example': "true"}, description="Новое значение для флага (e.g., 'true' or 'false')")

# --- Схемы для Летописца ---
class AuditLog(BaseModel):
    log_id: uuid.UUID
    actor_id: Optional[str] = None
    action: str
    target_entity: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
