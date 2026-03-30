# backend/models.py

# --- ИЗМЕНЕНИЕ: Добавлен импорт uuid для генерации ID на стороне приложения ---
import uuid
from datetime import timedelta
# --- ИЗМЕНЕНИЕ: Импортируем универсальный UUID вместо специфичного для PostgreSQL ---
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Boolean, 
    ForeignKey, text, Numeric, UUID, Text, Index, CheckConstraint, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# --- ПРИНЦИП 1: Разделение сущностей "Справочник" vs "Экземпляр" ---
# Мы отделяем описание напитка от конкретной кеги.
# Это позволяет нам легко управлять ассортиментом и анализировать продажи по напиткам.

class Beverage(Base):
    """
    СПРАВОЧНИК НАПИТКОВ.
    Хранит уникальные характеристики каждого напитка, который мы продаем.
    """
    __tablename__ = "beverages"

    # --- ИЗМЕНЕНИЕ: Генерация UUID теперь выполняется кодом Python (default=uuid.uuid4) ---
    beverage_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False, comment="Название напитка, e.g., 'Heineken'")
    brewery = Column(String(100), comment="Пивоварня")
    style = Column(String(50), comment="Стиль, e.g., 'Lager', 'IPA'")
    abv = Column(Numeric(4, 2), comment="Крепость (Alcohol By Volume)")
    sell_price_per_liter = Column(Numeric(10, 2), nullable=False, comment="Розничная цена за литр")

    # Связь "один ко многим": один напиток может быть во многих кегах
    description_short = Column(Text, nullable=True)
    ibu = Column(Numeric(5, 2), nullable=True)
    display_brand_name = Column(String(100), nullable=True)
    accent_color = Column(String(32), nullable=True)
    background_asset_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.asset_id"), nullable=True)
    logo_asset_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.asset_id"), nullable=True)
    text_theme = Column(String(16), nullable=True)
    price_display_mode_default = Column(String(16), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    kegs = relationship("Keg", back_populates="beverage")
    background_asset = relationship("MediaAsset", foreign_keys=[background_asset_id])
    logo_asset = relationship("MediaAsset", foreign_keys=[logo_asset_id])


# --- ОСНОВНЫЕ ОПЕРАЦИОННЫЕ МОДЕЛИ ---

class Keg(Base):
    """
    ЭКЗЕМПЛЯР КЕГИ.
    Представляет физическую кегу с конкретным напитком.
    """
    __tablename__ = "kegs"

    # --- ИЗМЕНЕНИЕ: Генерация UUID теперь выполняется кодом Python ---
    keg_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beverage_id = Column(UUID(as_uuid=True), ForeignKey("beverages.beverage_id"), nullable=False, index=True)
    
    initial_volume_ml = Column(Integer, nullable=False, comment="Начальный объем в миллилитрах")
    current_volume_ml = Column(Integer, nullable=False, comment="Текущий остаток в миллилитрах")
    purchase_price = Column(Numeric(10, 2), nullable=False, comment="Закупочная стоимость всей кеги")

    # ПРИНЦИП 2: Конечный автомат (статусы)
    status = Column(String(20), nullable=False, default='full', index=True, comment="Статус: full, in_use, empty")

    tapped_at = Column(DateTime(timezone=True), comment="Время подключения к крану")
    finished_at = Column(DateTime(timezone=True), comment="Время, когда кега закончилась")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь "многие к одному": многие кеги могут быть одного типа напитка
    beverage = relationship("Beverage", back_populates="kegs")
    # Связь "один к одному": одна кега может быть подключена только к одному крану
    tap = relationship("Tap", back_populates="keg", uselist=False)
    # Связь "один ко многим": из одной кеги может быть много наливов
    pours = relationship("Pour", back_populates="keg")
    non_sale_flows = relationship("NonSaleFlow", back_populates="keg")


class Tap(Base):
    """
    ФИЗИЧЕСКИЙ КРАН.
    Представляет точку розлива в баре.
    """
    __tablename__ = "taps"

    tap_id = Column(Integer, primary_key=True) # Используем простой Integer для легкой идентификации
    keg_id = Column(UUID(as_uuid=True), ForeignKey("kegs.keg_id"), nullable=True, unique=True)
    display_name = Column(String(50), nullable=False, unique=True, comment="Имя крана для UI, e.g., 'Кран 1'")
    
    # ПРИНЦИП 2: Конечный автомат (статусы)
    status = Column(String(20), nullable=False, default='locked', index=True, comment="Статус: active, locked, cleaning, empty")

    last_cleaned_at = Column(DateTime(timezone=True))

    # Связь "один к одному": к одному крану подключена одна кега
    keg = relationship("Keg", back_populates="tap")
    # Связь "один ко многим": с одного крана может быть много наливов
    pours = relationship("Pour", back_populates="tap")
    non_sale_flows = relationship("NonSaleFlow", back_populates="tap")
    display_config = relationship("TapDisplayConfig", back_populates="tap", uselist=False, cascade="all, delete-orphan")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    asset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String(32), nullable=False, index=True)
    storage_key = Column(String(255), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    byte_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    checksum_sha256 = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TapDisplayConfig(Base):
    __tablename__ = "tap_display_configs"

    tap_id = Column(Integer, ForeignKey("taps.tap_id", ondelete="CASCADE"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    idle_instruction = Column(Text, nullable=True)
    fallback_title = Column(String(120), nullable=True)
    fallback_subtitle = Column(Text, nullable=True)
    maintenance_title = Column(String(120), nullable=True)
    maintenance_subtitle = Column(Text, nullable=True)
    override_accent_color = Column(String(32), nullable=True)
    override_background_asset_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.asset_id"), nullable=True)
    show_price_mode = Column(String(16), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    tap = relationship("Tap", back_populates="display_config")
    override_background_asset = relationship("MediaAsset", foreign_keys=[override_background_asset_id])


class Guest(Base):
    """
    ГОСТЬ.
    Представляет клиента бара.
    """
    __tablename__ = "guests"

    # --- ИЗМЕНЕНИЕ: Генерация UUID теперь выполняется кодом Python ---
    guest_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    last_name = Column(String(50), nullable=False, index=True)
    first_name = Column(String(50), nullable=False)
    patronymic = Column(String(50), nullable=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    id_document = Column(String(100), nullable=False, index=True) # Убрал unique=True, т.к. один документ может быть у нескольких гостей (теоретически)
    balance = Column(Numeric(10, 2), nullable=False, default=0.00) # --- ИЗМЕНЕНИЕ: Заменил server_default на default для совместимости ---
    is_active = Column(Boolean, nullable=False, default=True) # --- ИЗМЕНЕНИЕ: Заменил server_default на default ---
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Связи "один ко многим"
    cards = relationship("Card", back_populates="guest")
    visits = relationship("Visit", back_populates="guest")
    transactions = relationship("Transaction", back_populates="guest")
    pours = relationship("Pour", back_populates="guest")


class Card(Base):
    """
    RFID-КАРТА.
    Физический носитель из пула, временно назначаемый на визит.
    """
    __tablename__ = "cards"

    card_uid = Column(String(50), primary_key=True, comment="Уникальный идентификатор, читаемый с карты")
    # Legacy compatibility field only. Operational ownership now lives on Visit.card_uid.
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=True, index=True)

    # Inventory lifecycle: available -> assigned_to_visit -> returned_to_pool / lost / retired.
    status = Column(
        String(32),
        nullable=False,
        default='available',
        index=True,
        comment="Статус: available, assigned_to_visit, returned_to_pool, lost, retired",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Связь "многие к одному": многие карты могут принадлежать одному гостю
    guest = relationship("Guest", back_populates="cards")
    # Связь "один ко многим": одной картой можно сделать много наливов
    visits = relationship("Visit", back_populates="card")
    pours = relationship("Pour", back_populates="card")


class Visit(Base):
    """
    ВИЗИТ ГОСТЯ.
    Операционная сессия в рамках одного посещения.
    """
    __tablename__ = "visits"

    visit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=False, index=True)
    card_uid = Column(String(50), ForeignKey("cards.card_uid"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    operational_status = Column(
        String(32),
        nullable=False,
        default="active_assigned",
        index=True,
        comment="Сервисное состояние: active_assigned, active_blocked_lost_card, closed_ok, closed_missing_card",
    )
    opened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_reason = Column(Text, nullable=True)
    # M3 placeholder: intentionally no FK for M2.
    active_tap_id = Column(Integer, nullable=True)
    lock_set_at = Column(DateTime(timezone=True), nullable=True)
    card_returned = Column(Boolean, nullable=False, default=True)
    returned_at = Column(DateTime(timezone=True), nullable=True)
    returned_by = Column(String(100), nullable=True)
    return_method = Column(String(32), nullable=True)

    guest = relationship("Guest", back_populates="visits")
    card = relationship("Card", back_populates="visits")
    pours = relationship("Pour", back_populates="visit")


class LostCard(Base):
    __tablename__ = "lost_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_uid = Column(String(50), nullable=False, unique=True, index=True)
    reported_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    reported_by = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    visit_id = Column(UUID(as_uuid=True), ForeignKey("visits.visit_id"), nullable=True, index=True)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=True, index=True)


# --- ПРИНЦИП 3: Транзакционная модель для всех изменений ---
# Все изменения баланса и объема являются неизменяемыми записями (транзакциями).


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (
        Index(
            "uq_shifts_one_open",
            "status",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
        CheckConstraint("status IN ('open', 'closed')", name="ck_shifts_status_values"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    opened_by = Column(String(100), nullable=True)
    closed_by = Column(String(100), nullable=True)


class ShiftReport(Base):
    __tablename__ = "shift_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(1), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    payload = Column(JSON, nullable=False)


class Pour(Base):
    """
    ТРАНЗАКЦИЯ НАЛИВА.
    Неизменяемая запись о каждом факте налива.
    """
    __tablename__ = "pours"

    # --- ИЗМЕНЕНИЕ: Генерация UUID теперь выполняется кодом Python ---
    pour_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_tx_id = Column(String(100), unique=True, nullable=False, index=True, comment="Идентификатор от RPi для идемпотентности")
    
    # Внешние ключи для связи с другими сущностями
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=False, index=True)
    card_uid = Column(String(50), ForeignKey("cards.card_uid"), nullable=False, index=True)
    visit_id = Column(UUID(as_uuid=True), ForeignKey("visits.visit_id"), nullable=True, index=True)
    tap_id = Column(Integer, ForeignKey("taps.tap_id"), nullable=False)
    keg_id = Column(UUID(as_uuid=True), ForeignKey("kegs.keg_id"), nullable=False, index=True)
    
    # Детали транзакции
    volume_ml = Column(Integer, nullable=False)
    # --- ИЗМЕНЕНИЕ: Убрал price_per_ml_at_pour, т.к. amount_charged достаточно. Можно вернуть при необходимости. ---
    amount_charged = Column(Numeric(10, 2), nullable=False, comment="Списанная сумма")
    price_per_ml_at_pour = Column(Numeric(10, 4), nullable=False, comment="Цена за мл на момент налива")
    duration_ms = Column(Integer, nullable=True)
    sync_status = Column(String(20), nullable=False, default="synced", index=True)
    short_id = Column(String(8), nullable=True, index=True)
    is_manual_reconcile = Column(Boolean, nullable=False, default=False)
    
    # Временные метки
    poured_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи "многие к одному"
    guest = relationship("Guest", back_populates="pours")
    card = relationship("Card", back_populates="pours")
    visit = relationship("Visit", back_populates="pours")
    tap = relationship("Tap", back_populates="pours")
    keg = relationship("Keg", back_populates="pours")

    @property
    def beverage(self):
        return self.keg.beverage if self.keg else None



    @property
    def ended_at(self):
        return self.synced_at or self.reconciled_at

    @property
    def started_at(self):
        ended_at = self.ended_at
        if ended_at is None or self.duration_ms is None:
            return None
        return ended_at - timedelta(milliseconds=self.duration_ms)


class NonSaleFlow(Base):
    __tablename__ = "non_sale_flows"
    __table_args__ = (
        CheckConstraint("volume_ml >= 0", name="ck_non_sale_flows_volume_non_negative"),
        CheckConstraint("accounted_volume_ml >= 0", name="ck_non_sale_flows_accounted_volume_non_negative"),
    )

    non_sale_flow_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(128), nullable=False, unique=True, index=True)
    tap_id = Column(Integer, ForeignKey("taps.tap_id"), nullable=False, index=True)
    keg_id = Column(UUID(as_uuid=True), ForeignKey("kegs.keg_id"), nullable=True, index=True)

    volume_ml = Column(Integer, nullable=False, default=0)
    accounted_volume_ml = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=False, default=0)

    flow_category = Column(String(64), nullable=False, index=True)
    session_state = Column(String(64), nullable=False)
    reason = Column(String(128), nullable=False)
    card_present = Column(Boolean, nullable=False, default=False)
    valve_open = Column(Boolean, nullable=False, default=False)
    card_uid = Column(String(50), nullable=True, index=True)
    short_id = Column(String(8), nullable=True, index=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    tap = relationship("Tap", back_populates="non_sale_flows")
    keg = relationship("Keg", back_populates="non_sale_flows")

class Transaction(Base):
    """
    ФИНАНСОВАЯ ТРАНЗАКЦИЯ.
    Неизменяемая запись о пополнении баланса, возврате и т.д.
    """
    __tablename__ = "transactions"

    # --- ИЗМЕНЕНИЕ: Генерация UUID теперь выполняется кодом Python ---
    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.guest_id"), nullable=False, index=True)
    visit_id = Column(UUID(as_uuid=True), ForeignKey("visits.visit_id"), nullable=True, index=True)
    
    amount = Column(Numeric(10, 2), nullable=False, comment="Сумма транзакции. Положительная для пополнения.")
    type = Column(String(20), nullable=False, comment="Тип: top-up, refund, correction")
    payment_method = Column(String(20), nullable=True, comment="Метод оплаты: cash, card")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    guest = relationship("Guest", back_populates="transactions")
    visit = relationship("Visit")


# --- СИСТЕМНЫЕ МОДЕЛИ ---

class AuditLog(Base):
    """
    ЖУРНАЛ АУДИТА.
    Записывает все важные действия администраторов и барменов.
    """
    __tablename__ = "audit_logs"

    # --- ИЗМЕНЕНИЕ: Генерация UUID теперь выполняется кодом Python ---
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(String, nullable=True, comment="ID пользователя, совершившего действие")
    action = Column(String, nullable=False, index=True, comment="Тип действия, e.g., 'create_keg'")
    target_entity = Column(String, comment="Сущность, над которой совершено действие, e.g., 'Keg'")
    target_id = Column(String, comment="ID целевой сущности")
    details = Column(Text, comment="Детали действия в формате JSON") # --- ИЗМЕНЕНИЕ: String -> Text для большей вместимости ---
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

# --- МОДЕЛИ КОНТРОЛЛЕРОВ ---

class Controller(Base):
    """
    КОНТРОЛЛЕР (RPi).
    Представляет физическое устройство (Raspberry Pi), управляющее краном.
    """
    __tablename__ = "controllers"

    # Уникальный ID контроллера, который он сам о себе знает (e.g., MAC-адрес).
    # Используем String, так как это естественный ключ, предоставляемый устройством.
    controller_id = Column(String(50), primary_key=True, index=True)
    
    # Информация, которую контроллер периодически сообщает о себе
    ip_address = Column(String(45), nullable=False, comment="Текущий IP-адрес устройства в сети")
    firmware_version = Column(String(20), nullable=True, comment="Версия прошивки на устройстве")
    
    # Метаданные, управляемые сервером
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Время первой регистрации контроллера")
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Время последнего 'check-in' от контроллера")

# --- МОДЕЛЬ СОСТОЯНИЯ СИСТЕМЫ ---
class SystemState(Base):
    """
    ГЛОБАЛЬНОЕ СОСТОЯНИЕ СИСТЕМЫ.
    Key-Value хранилище для глобальных флагов, таких как экстренная остановка.
    """
    __tablename__ = "system_states"

    # Ключ настройки, e.g., 'emergency_stop_enabled'
    key = Column(String(50), primary_key=True, index=True)
    # Значение настройки, хранится как строка, e.g., 'true', 'false'
    value = Column(String(255), nullable=False)



class IncidentState(Base):
    """
    DURABLE INCIDENT OVERLAY.
    Stores server-confirmed operator workflow state for aggregated incidents.
    """
    __tablename__ = "incident_states"

    incident_id = Column(String(255), primary_key=True)
    status = Column(String(20), nullable=False, default="new", index=True)
    owner = Column(String(100), nullable=True)
    last_action = Column(String(64), nullable=True)
    last_action_at = Column(DateTime(timezone=True), nullable=True)
    last_note = Column(Text, nullable=True)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    escalation_reason = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closure_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
