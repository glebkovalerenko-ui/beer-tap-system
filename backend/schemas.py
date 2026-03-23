# backend/schemas.py
import re
import uuid
# --- ИЗМЕНЕНИЕ: Добавлен импорт ConfigDict для современного синтаксиса Pydantic v2 ---
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Literal

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
DISPLAY_TEXT_THEMES = {"light", "dark"}
DISPLAY_PRICE_MODES = {"per_100ml", "per_liter", "auto"}
DISPLAY_MEDIA_KINDS = {"background", "logo"}


def _normalize_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_accent_color(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    if not HEX_COLOR_PATTERN.fullmatch(normalized):
        raise ValueError("accent_color must be a hex color like #AABBCC")
    return normalized.upper()


def _validate_display_text_theme(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    if normalized not in DISPLAY_TEXT_THEMES:
        raise ValueError("text_theme must be one of: light, dark")
    return normalized


def _validate_display_price_mode(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    if normalized not in DISPLAY_PRICE_MODES:
        raise ValueError("price mode must be one of: per_100ml, per_liter, auto")
    return normalized


def _validate_media_kind(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in DISPLAY_MEDIA_KINDS:
        raise ValueError("kind must be one of: background, logo")
    return normalized

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
    description_short: Optional[str] = Field(default=None, max_length=160)
    ibu: Optional[Decimal] = Field(default=None)
    display_brand_name: Optional[str] = Field(default=None)
    accent_color: Optional[str] = Field(default=None)
    background_asset_id: Optional[uuid.UUID] = None
    logo_asset_id: Optional[uuid.UUID] = None
    text_theme: Optional[str] = None
    price_display_mode_default: Optional[str] = None

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_accent_color(value)

    @field_validator("text_theme")
    @classmethod
    def validate_text_theme(cls, value: Optional[str]) -> Optional[str]:
        return _validate_display_text_theme(value)

    @field_validator("price_display_mode_default")
    @classmethod
    def validate_price_display_mode_default(cls, value: Optional[str]) -> Optional[str]:
        return _validate_display_price_mode(value)

class BeverageCreate(BeverageBase):
    pass


class BeverageUpdate(BaseModel):
    name: Optional[str] = None
    brewery: Optional[str] = None
    style: Optional[str] = None
    abv: Optional[Decimal] = None
    sell_price_per_liter: Optional[Decimal] = None
    description_short: Optional[str] = Field(default=None, max_length=160)
    ibu: Optional[Decimal] = None
    display_brand_name: Optional[str] = None
    accent_color: Optional[str] = None
    background_asset_id: Optional[uuid.UUID] = None
    logo_asset_id: Optional[uuid.UUID] = None
    text_theme: Optional[str] = None
    price_display_mode_default: Optional[str] = None

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_accent_color(value)

    @field_validator("text_theme")
    @classmethod
    def validate_text_theme(cls, value: Optional[str]) -> Optional[str]:
        return _validate_display_text_theme(value)

    @field_validator("price_display_mode_default")
    @classmethod
    def validate_price_display_mode_default(cls, value: Optional[str]) -> Optional[str]:
        return _validate_display_price_mode(value)

    @model_validator(mode="after")
    def validate_has_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self

class Beverage(BeverageBase):
    beverage_id: uuid.UUID
    # --- ИЗМЕНЕНИЕ: 'class Config' заменен на 'model_config' ---
    model_config = ConfigDict(from_attributes=True)


class MediaAssetCreateResponse(BaseModel):
    asset_id: uuid.UUID
    kind: str
    storage_key: str
    original_filename: str
    mime_type: str
    byte_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    checksum_sha256: str
    content_url: str
    created_at: datetime

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        return _validate_media_kind(value)

    model_config = ConfigDict(from_attributes=True)


class MediaAssetListItem(BaseModel):
    asset_id: uuid.UUID
    kind: str
    original_filename: str
    mime_type: str
    byte_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    checksum_sha256: str
    content_url: str
    created_at: datetime

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        return _validate_media_kind(value)

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


class KegSuggestionResponse(BaseModel):
    recommended_keg: Optional[Keg] = None
    candidates_count: int
    reason: str
    ordering_keys_used: list[str]

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


class TapDisplayConfigBase(BaseModel):
    enabled: bool = True
    idle_instruction: Optional[str] = None
    fallback_title: Optional[str] = None
    fallback_subtitle: Optional[str] = None
    maintenance_title: Optional[str] = None
    maintenance_subtitle: Optional[str] = None
    override_accent_color: Optional[str] = None
    override_background_asset_id: Optional[uuid.UUID] = None
    show_price_mode: Optional[str] = None

    @field_validator("override_accent_color")
    @classmethod
    def validate_override_accent_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_accent_color(value)

    @field_validator("show_price_mode")
    @classmethod
    def validate_show_price_mode(cls, value: Optional[str]) -> Optional[str]:
        return _validate_display_price_mode(value)


class TapDisplayConfigUpsert(TapDisplayConfigBase):
    pass


class TapDisplayConfig(TapDisplayConfigBase):
    tap_id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Tap(TapBase):
    tap_id: int
    status: str
    keg_id: Optional[uuid.UUID] = None
    keg: Optional[Keg] = None
    model_config = ConfigDict(from_attributes=True)


class DisplaySnapshotAsset(BaseModel):
    asset_id: uuid.UUID
    kind: str
    checksum_sha256: str
    content_url: str
    width: Optional[int] = None
    height: Optional[int] = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        return _validate_media_kind(value)


class DisplaySnapshotTap(BaseModel):
    tap_id: int
    display_name: str
    status: str
    enabled: bool


class DisplaySnapshotServiceFlags(BaseModel):
    emergency_stop: bool


class DisplaySnapshotAssignment(BaseModel):
    keg_id: Optional[uuid.UUID] = None
    beverage_id: Optional[uuid.UUID] = None
    has_assignment: bool


class DisplaySnapshotPresentation(BaseModel):
    name: Optional[str] = None
    brand_name: Optional[str] = None
    brewery: Optional[str] = None
    style: Optional[str] = None
    abv: Optional[Decimal] = None
    description_short: Optional[str] = None


class DisplaySnapshotPricing(BaseModel):
    sell_price_per_liter: Optional[Decimal] = None
    price_per_100ml_cents: Optional[int] = None
    display_mode: str
    display_text: Optional[str] = None


class DisplaySnapshotTheme(BaseModel):
    accent_color: Optional[str] = None
    text_theme: Optional[str] = None
    background_asset: Optional[DisplaySnapshotAsset] = None
    logo_asset: Optional[DisplaySnapshotAsset] = None


class DisplaySnapshotCopy(BaseModel):
    idle_instruction: Optional[str] = None
    fallback_title: Optional[str] = None
    fallback_subtitle: Optional[str] = None
    maintenance_title: Optional[str] = None
    maintenance_subtitle: Optional[str] = None


class DisplayTapSnapshot(BaseModel):
    tap: DisplaySnapshotTap
    service_flags: DisplaySnapshotServiceFlags
    assignment: DisplaySnapshotAssignment
    presentation: DisplaySnapshotPresentation
    pricing: DisplaySnapshotPricing
    theme: DisplaySnapshotTheme
    copy_block: DisplaySnapshotCopy = Field(alias="copy", serialization_alias="copy")
    content_version: str
    generated_at: datetime
    model_config = ConfigDict(populate_by_name=True)

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


class VisitReportLostCardRequest(BaseModel):
    reason: Optional[str] = Field(default=None, json_schema_extra={'example': "guest_reported_loss"})
    comment: Optional[str] = Field(default=None, json_schema_extra={'example': "Guest says card was lost outside bar"})


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


class Shift(BaseModel):
    id: uuid.UUID
    opened_at: datetime
    closed_at: Optional[datetime] = None
    status: str
    opened_by: Optional[str] = None
    closed_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ShiftCurrentResponse(BaseModel):
    status: Literal["open", "closed"]
    shift: Optional[Shift] = None


class ShiftReportMeta(BaseModel):
    shift_id: uuid.UUID
    report_type: Literal["X", "Z"]
    generated_at: datetime
    opened_at: datetime
    closed_at: Optional[datetime] = None


class ShiftReportTotals(BaseModel):
    pours_count: int
    total_volume_ml: int
    total_amount_cents: int
    new_guests_count: int
    pending_sync_count: int
    reconciled_count: int
    mismatch_count: int


class ShiftReportByTapItem(BaseModel):
    tap_id: int
    pours_count: int
    volume_ml: int
    amount_cents: int
    pending_sync_count: int


class ShiftReportVisits(BaseModel):
    active_visits_count: int
    closed_visits_count: int


class ShiftReportKegs(BaseModel):
    status: str
    note: str


class ShiftReportPayload(BaseModel):
    meta: ShiftReportMeta
    totals: ShiftReportTotals
    by_tap: list[ShiftReportByTapItem]
    visits: ShiftReportVisits
    kegs: ShiftReportKegs


class ShiftReportDocument(BaseModel):
    report_id: uuid.UUID
    shift_id: uuid.UUID
    report_type: Literal["X", "Z"]
    generated_at: datetime
    payload: ShiftReportPayload
    model_config = ConfigDict(from_attributes=True)


class ShiftZReportListItem(BaseModel):
    report_id: uuid.UUID
    shift_id: uuid.UUID
    generated_at: datetime
    total_volume_ml: int
    total_amount_cents: int
    pours_count: int
    active_visits_count: int
    closed_visits_count: int




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
    projected_remaining_allowance_ml: Optional[int] = None
    projected_remaining_allowance_source: Optional[str] = None
    allowance_calculation_note: Optional[str] = None
    price_per_ml_cents: Optional[int] = None

class VisitPourAuthorizeRequest(BaseModel):
    card_uid: str = Field(..., json_schema_extra={'example': "04AB7815CD6B80"})
    tap_id: int = Field(..., ge=1, json_schema_extra={'example': 1})


class VisitPourAuthorizeResponse(BaseModel):
    allowed: bool
    visit: Optional[Visit] = None
    reason: Optional[str] = None
    guest_first_name: Optional[str] = None
    min_start_ml: int = 20
    max_volume_ml: int = 0
    price_per_ml_cents: int = 0
    balance_cents: int = 0
    allowed_overdraft_cents: int = 0
    safety_ml: int = 2
    lock_set_at: Optional[datetime] = None


class LostCardCreateRequest(BaseModel):
    card_uid: str = Field(..., min_length=1, json_schema_extra={'example': "04AB7815CD6B80"})
    reported_by: Optional[str] = Field(default=None, json_schema_extra={'example': "operator_1"})
    reason: Optional[str] = Field(default=None, json_schema_extra={'example': "guest_reported_loss"})
    comment: Optional[str] = Field(default=None, json_schema_extra={'example': "Reported from front desk"})
    visit_id: Optional[uuid.UUID] = None
    guest_id: Optional[uuid.UUID] = None


class LostCard(BaseModel):
    id: uuid.UUID
    card_uid: str
    reported_at: datetime
    reported_by: Optional[str] = None
    reason: Optional[str] = None
    comment: Optional[str] = None
    visit_id: Optional[uuid.UUID] = None
    guest_id: Optional[uuid.UUID] = None
    model_config = ConfigDict(from_attributes=True)


class LostCardRestoreResponse(BaseModel):
    card_uid: str
    restored: bool = True


class CardResolveLostCard(BaseModel):
    reported_at: datetime
    comment: Optional[str] = None
    visit_id: Optional[uuid.UUID] = None
    reported_by: Optional[str] = None
    reason: Optional[str] = None
    guest_id: Optional[uuid.UUID] = None


class CardResolveActiveVisit(BaseModel):
    visit_id: uuid.UUID
    guest_id: uuid.UUID
    guest_full_name: str
    phone_number: str
    status: str
    card_uid: Optional[str] = None
    active_tap_id: Optional[int] = None
    opened_at: datetime


class CardResolveGuest(BaseModel):
    guest_id: uuid.UUID
    full_name: str
    phone_number: str
    balance_cents: int


class CardResolveCard(BaseModel):
    uid: str
    status: str
    guest_id: Optional[uuid.UUID] = None


class CardResolveResponse(BaseModel):
    card_uid: str
    is_lost: bool
    lost_card: Optional[CardResolveLostCard] = None
    active_visit: Optional[CardResolveActiveVisit] = None
    guest: Optional[CardResolveGuest] = None
    card: Optional[CardResolveCard] = None
    recommended_action: Literal["lost_restore", "open_active_visit", "open_new_visit", "bind_card", "unknown"]




class SessionHistoryFilterParams(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tap_id: Optional[int] = None
    status: Optional[str] = None
    card_uid: Optional[str] = None
    incident_only: bool = False
    unsynced_only: bool = False


class SessionLifecycleTimestamps(BaseModel):
    opened_at: datetime
    first_authorized_at: Optional[datetime] = None
    first_pour_started_at: Optional[datetime] = None
    last_pour_ended_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    last_operator_action_at: Optional[datetime] = None


class SessionOperatorAction(BaseModel):
    timestamp: datetime
    action: str
    actor_id: Optional[str] = None
    label: str
    details: Optional[str] = None


class SessionNarrativeEvent(BaseModel):
    timestamp: datetime
    kind: str
    title: str
    description: str
    status: Optional[str] = None
    actor_id: Optional[str] = None


class SessionHistoryListItem(BaseModel):
    visit_id: uuid.UUID
    guest_id: uuid.UUID
    guest_full_name: str
    phone_number: Optional[str] = None
    card_uid: Optional[str] = None
    visit_status: str
    operator_status: str
    completion_source: Optional[str] = None
    sync_state: str
    primary_tap_id: Optional[int] = None
    taps: list[int] = []
    incident_count: int = 0
    has_incident: bool = False
    has_unsynced: bool = False
    contains_tail_pour: bool = False
    contains_non_sale_flow: bool = False
    opened_at: datetime
    closed_at: Optional[datetime] = None
    last_event_at: datetime
    operator_actions: list[SessionOperatorAction] = []
    lifecycle: SessionLifecycleTimestamps


class SessionHistoryDetail(SessionHistoryListItem):
    narrative: list[SessionNarrativeEvent] = []

class VisitReportLostCardResponse(BaseModel):
    visit: Visit
    lost_card: LostCard
    lost: bool = True
    already_marked: bool = False


class VisitForceUnlockRequest(BaseModel):
    reason: str = Field(..., min_length=1, json_schema_extra={'example': "controller_offline_recovery"})
    comment: Optional[str] = Field(default=None, json_schema_extra={'example': "Manual unlock after timeout"})


class VisitReconcilePourRequest(BaseModel):
    tap_id: int = Field(..., ge=1, json_schema_extra={'example': 1})
    short_id: str = Field(..., min_length=6, max_length=8, json_schema_extra={'example': "A1B2C3"})
    volume_ml: int = Field(..., ge=1, json_schema_extra={'example': 250})
    amount: Decimal = Field(..., gt=0, json_schema_extra={'example': 175.00})
    duration_ms: Optional[int] = Field(default=None, ge=0, json_schema_extra={'example': 5000})
    reason: str = Field(..., min_length=1, json_schema_extra={'example': "sync_timeout"})
    comment: Optional[str] = Field(default=None, json_schema_extra={'example': "Operator entered from controller screen"})

class TopUpRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, json_schema_extra={'example': 500.00}, description="Сумма пополнения, должна быть больше нуля")
    payment_method: str = Field(..., json_schema_extra={'example': "cash"}, description="Метод оплаты (e.g., 'cash', 'card')")


class RefundRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, json_schema_extra={'example': 150.00}, description="Refund amount must be greater than zero")
    payment_method: str = Field(..., json_schema_extra={'example': "cash"}, description="Refund payment method")
    reason: Optional[str] = Field(default=None, json_schema_extra={'example': "demo_refund"})

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
    duration_ms: Optional[int] = None
    sync_status: str
    short_id: Optional[str] = None
    is_manual_reconcile: bool = False
    poured_at: datetime
    authorized_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    reconciled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
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
class LivePourFeedGuest(BaseModel):
    guest_id: uuid.UUID
    last_name: str
    first_name: str
    model_config = ConfigDict(from_attributes=True)


class LivePourFeedItem(BaseModel):
    item_id: str
    item_type: Literal["pour", "flow_event"]
    status: str
    tap_id: int
    tap_name: Optional[str] = None
    timestamp: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    volume_ml: int = 0
    amount_charged: Optional[Decimal] = None
    short_id: Optional[str] = None
    guest: Optional[LivePourFeedGuest] = None
    beverage_name: Optional[str] = None
    card_uid: Optional[str] = None
    card_present: Optional[bool] = None
    session_state: Optional[str] = None
    valve_open: Optional[bool] = None
    reason: Optional[str] = None
    event_status: Optional[str] = None


class FlowSummaryBreakdownItem(BaseModel):
    reason_code: str
    volume_ml: int


class TapFlowSummaryItem(BaseModel):
    tap_id: int
    tap_name: Optional[str] = None
    sale_volume_ml: int
    non_sale_volume_ml: int
    total_volume_ml: int
    non_sale_breakdown: list[FlowSummaryBreakdownItem] = []


class FlowSummaryResponse(BaseModel):
    sale_volume_ml: int
    non_sale_volume_ml: int
    total_volume_ml: int
    non_sale_breakdown: list[FlowSummaryBreakdownItem] = []
    by_tap: list[TapFlowSummaryItem] = []


class TodaySummaryResponse(BaseModel):
    period: Literal["day", "shift"]
    summary_complete: bool
    fallback_copy: Optional[str] = None
    shift_id: Optional[uuid.UUID] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    generated_at: datetime
    sessions_count: int
    volume_ml: int
    revenue: Decimal


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
    duration_ms: Optional[int] = Field(default=None, ge=0)
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    volume_ml: int
    tail_volume_ml: int = Field(default=0, ge=0)
    price_cents: int

    @model_validator(mode="after")
    def validate_duration_or_legacy_range(self):
        if self.tail_volume_ml > self.volume_ml:
            raise ValueError("tail_volume_ml must not exceed volume_ml")

        if self.duration_ms is not None:
            return self

        if self.start_ts is not None and self.end_ts is not None:
            return self

        raise ValueError("Either duration_ms or both start_ts/end_ts must be provided")

class SyncRequest(BaseModel):
    pours: list[PourData]

class SyncResult(BaseModel):
    client_tx_id: str
    status: str
    outcome: Optional[str] = None
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


class ControllerFlowEventRequest(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=128, json_schema_extra={"example": "tap-1-flow-1741612045000"})
    event_status: Literal["started", "updated", "stopped"] = Field(
        ...,
        json_schema_extra={"example": "updated"},
    )
    tap_id: int = Field(..., ge=1, json_schema_extra={"example": 1})
    volume_ml: int = Field(..., ge=1, json_schema_extra={"example": 15})
    duration_ms: int = Field(default=0, ge=0, json_schema_extra={"example": 1800})
    card_present: bool = Field(default=False)
    valve_open: bool = Field(default=False)
    session_state: str = Field(..., min_length=1, max_length=64, json_schema_extra={"example": "no_card_no_session"})
    card_uid: Optional[str] = Field(default=None, min_length=1, max_length=64, json_schema_extra={"example": "04AB7815CD6B80"})
    short_id: Optional[str] = Field(default=None, min_length=6, max_length=8, json_schema_extra={"example": "A1B2C3D4"})
    reason: str = Field(
        ...,
        min_length=1,
        max_length=128,
        json_schema_extra={"example": "flow_detected_when_valve_closed_without_active_session"},
    )


class ControllerFlowEventResponse(BaseModel):
    accepted: bool = True

# --- Схемы для Глобального Состояния Системы ---
class SystemStateItem(BaseModel):
    key: str
    value: str


class IncidentListItem(BaseModel):
    incident_id: str
    priority: Literal["low", "medium", "high", "critical"]
    created_at: datetime
    tap: Optional[str] = None
    type: str
    status: Literal["new", "in_progress", "closed"]
    operator: Optional[str] = None
    note_action: Optional[str] = None
    source: Optional[str] = None
    owner: Optional[str] = None
    last_action: Optional[str] = None
    last_action_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    closed_at: Optional[datetime] = None
    closure_summary: Optional[str] = None


class IncidentClaimPayload(BaseModel):
    owner: str = Field(..., min_length=1, max_length=100)
    note: Optional[str] = Field(default=None, max_length=4000)


class IncidentNotePayload(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


class IncidentEscalationPayload(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4000)
    note: Optional[str] = Field(default=None, max_length=4000)


class IncidentClosePayload(BaseModel):
    resolution_summary: str = Field(..., min_length=1, max_length=4000)
    note: Optional[str] = Field(default=None, max_length=4000)


class SystemDeviceHealth(BaseModel):
    device_id: str
    device_type: str
    tap: Optional[str] = None
    state: Literal["ok", "warning", "critical"]
    label: str
    detail: Optional[str] = None
    updated_at: Optional[datetime] = None


class SystemSubsystemSummary(BaseModel):
    name: str
    state: Literal["ok", "warning", "critical"]
    label: str
    detail: Optional[str] = None
    devices: list[SystemDeviceHealth] = []


class SystemOperationalSummary(BaseModel):
    emergency_stop: bool
    overall_state: Literal["ok", "warning", "critical"]
    generated_at: datetime
    open_incident_count: int = 0
    subsystems: list[SystemSubsystemSummary] = []

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
