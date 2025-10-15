# backend/schemas.py
import uuid
from pydantic import BaseModel, Field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

# =============================================================================
# СХЕМЫ ДЛЯ БИЗНЕС-ЛОГИКИ
# =============================================================================

# --- Схемы для Напитков (Beverage) ---
# ... (Этот раздел остается без изменений) ...
class BeverageBase(BaseModel):
    name: str = Field(..., example="Guinness")
    brewery: Optional[str] = Field(default=None, example="St. James's Gate Brewery")
    style: Optional[str] = Field(default=None, example="Stout")
    abv: Optional[Decimal] = Field(default=None, example=4.2)
    sell_price_per_liter: Decimal = Field(..., example=700.00)

class BeverageCreate(BeverageBase):
    pass

class Beverage(BeverageBase):
    beverage_id: uuid.UUID

    class Config:
        from_attributes = True

# --- Схемы для Кег (Keg) ---
# ... (Этот раздел остается без изменений) ...
class KegBase(BaseModel):
    initial_volume_ml: int = Field(..., example=50000)
    purchase_price: Decimal = Field(..., example=10000.00)

class KegCreate(KegBase):
    beverage_id: uuid.UUID

class KegUpdate(BaseModel):
    status: Optional[str] = Field(default=None, example="empty")

class Keg(KegBase):
    keg_id: uuid.UUID
    beverage_id: uuid.UUID
    current_volume_ml: int
    status: str
    tapped_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    beverage: Beverage

    class Config:
        from_attributes = True

# --- Схемы для Кранов (Tap) ---
# ... (Этот раздел остается без изменений) ...
class TapBase(BaseModel):
    display_name: str = Field(..., example="Кран №1")

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

    class Config:
        from_attributes = True

# =============================================================================
# ## ИЗМЕНЕННАЯ СЕКЦИЯ ##
# СХЕМЫ ДЛЯ КАРТ (Card) - Полностью синхронизированы с models.py
# =============================================================================
class CardCreate(BaseModel):
    """Схема для тела запроса при создании новой карты."""
    # Имя поля card_uid теперь совпадает с моделью.
    card_uid: str = Field(..., example="04AB7815CD6B80")

class Card(BaseModel):
    """Схема для ответа API. Поля ТОЧНО соответствуют атрибутам в models.Card."""
    card_uid: str
    guest_id: Optional[uuid.UUID] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# =============================================================================
# ## ИЗМЕНЕННАЯ СЕКЦИЯ ##
# СЛУЖЕБНЫЕ СХЕМЫ ДЛЯ API КАРТ
# =============================================================================
class CardAssign(BaseModel):
    """Схема для тела запроса на привязку карты к гостю."""
    # Имя поля card_uid теперь совпадает с моделью.
    card_uid: str = Field(..., example="04AB7815CD6B80")

class CardStatusUpdate(BaseModel):
    """Схема для тела запроса на изменение статуса карты."""
    status: str = Field(..., example="lost")

class TopUpRequest(BaseModel):
    """Схема для тела запроса на пополнение баланса."""
    amount: Decimal = Field(..., gt=0, example=500.00, description="Сумма пополнения, должна быть больше нуля")
    payment_method: str = Field(..., example="cash", description="Метод оплаты (e.g., 'cash', 'card')")

class HistoryItem(BaseModel):
    """Унифицированная схема для одной записи в истории гостя."""
    timestamp: datetime
    type: str = Field(..., example="pour | top-up")
    amount: Decimal = Field(..., description="Положительное для пополнений, отрицательное для наливов")
    details: str = Field(..., example="Налив: Guinness 500 мл | Пополнение: Наличные")

class GuestHistoryResponse(BaseModel):
    """Схема для полного ответа по истории операций гостя."""
    guest_id: uuid.UUID
    history: List[HistoryItem] = []

# --- Схемы для Финансовых Транзакций (Transaction) ---
# ... (Этот раздел остается без изменений) ...
class TransactionBase(BaseModel):
    amount: Decimal
    type: str = Field(..., example="top-up")
    payment_method: Optional[str] = Field(default=None, example="cash")

class TransactionCreate(TransactionBase):
    guest_id: uuid.UUID

class Transaction(TransactionBase):
    transaction_id: uuid.UUID
    guest_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        
# --- Схемы для Наливов (Pour) ---
# ... (Этот раздел остается без изменений) ...
class Pour(BaseModel):
    pour_id: uuid.UUID
    volume_ml: int
    amount_charged: Decimal
    poured_at: datetime
    
    class Config:
        from_attributes = True
        
# --- Схемы для Гостей (Guests) ---
class GuestBase(BaseModel):
    last_name: str = Field(..., example="Иванов")
    first_name: str = Field(..., example="Иван")
    patronymic: Optional[str] = Field(default=None, example="Иванович")
    phone_number: str = Field(..., example="+79211234567")
    date_of_birth: date = Field(..., example="1990-01-15")
    id_document: str = Field(..., example="4510 123456")

class GuestCreate(GuestBase):
    pass

class Guest(GuestBase):
    guest_id: uuid.UUID
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    ## ИЗМЕНЕННАЯ СЕКЦИЯ ##
    # Вложенная схема Card теперь использует правильное определение
    cards: List[Card] = []
    transactions: List[Transaction] = []
    pours: List[Pour] = []

    class Config:
        from_attributes = True

# --- Схемы для Синхронизации с Контроллером ---
# ... (Этот раздел остается без изменений) ...
class PourData(BaseModel):
    client_tx_id: str
    card_uid: str
    tap_id: int
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

# --- НОВЫЙ РАЗДЕЛ ---
# --- Схемы для Контроллеров (Controller) ---

class ControllerRegister(BaseModel):
    """Схема для тела запроса при регистрации контроллера (check-in)."""
    controller_id: str = Field(..., example="00:1A:2B:3C:4D:5E", description="Уникальный ID контроллера, e.g., MAC-адрес")
    ip_address: str = Field(..., example="192.168.1.101", description="Текущий IP-адрес контроллера в сети")
    firmware_version: Optional[str] = Field(default=None, example="1.0.2", description="Версия прошивки на устройстве")

class Controller(BaseModel):
    """Схема для ответа API. Представляет один зарегистрированный контроллер."""
    controller_id: str
    ip_address: str
    firmware_version: Optional[str] = None
    created_at: datetime
    last_seen: datetime

    class Config:
        from_attributes = True

# --- Схемы для Глобального Состояния Системы ---

class SystemStateItem(BaseModel):
    """Представляет один ключ-значение состояния системы."""
    key: str
    value: str

class SystemStateUpdate(BaseModel):
    """Схема для тела запроса на обновление состояния."""
    value: str = Field(..., example="true", description="Новое значение для флага (e.g., 'true' or 'false')")

# --- Схемы для Летописца ---

class AuditLog(BaseModel):
    """Схема для ответа API. Представляет одну запись в журнале аудита."""
    log_id: uuid.UUID
    actor_id: Optional[str] = None
    action: str
    target_entity: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True