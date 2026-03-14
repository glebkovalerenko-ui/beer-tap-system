import logging
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import system_crud
from media_storage import normalize_media_kind, storage_path_exists


EMERGENCY_STOP_KEY = "emergency_stop_enabled"
LOGGER = logging.getLogger("tap_display")

DEFAULT_IDLE_INSTRUCTION = "Приложите карту"
DEFAULT_FALLBACK_TITLE = "Кран недоступен"
DEFAULT_FALLBACK_SUBTITLE = "Обратитесь к оператору"
DEFAULT_MAINTENANCE_TITLE = "Кран временно недоступен"
DEFAULT_MAINTENANCE_SUBTITLE = "Обратитесь к оператору"
DEFAULT_ACCENT_COLOR = "#C79A3B"
DEFAULT_TEXT_THEME = "dark"

DISPLAY_MODE_PER_100ML = "per_100ml"
DISPLAY_MODE_PER_LITER = "per_liter"
DISPLAY_MODE_AUTO = "auto"
ALLOWED_PRICE_MODES = {DISPLAY_MODE_PER_100ML, DISPLAY_MODE_PER_LITER, DISPLAY_MODE_AUTO}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _decimal_to_text(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    normalized = format(quantized, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


def _price_per_100ml_cents(price_per_liter: Optional[Decimal]) -> Optional[int]:
    if price_per_liter is None:
        return None
    return int((price_per_liter * Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _resolve_price_mode(
    tap_override: Optional[str],
    beverage_default: Optional[str],
) -> str:
    candidate = tap_override or beverage_default or DISPLAY_MODE_PER_100ML
    if candidate not in ALLOWED_PRICE_MODES:
        return DISPLAY_MODE_PER_100ML
    if candidate == DISPLAY_MODE_AUTO:
        return DISPLAY_MODE_PER_100ML
    return candidate


def _format_price_display(price_per_liter: Optional[Decimal], display_mode: str) -> Optional[str]:
    if price_per_liter is None:
        return None
    if display_mode == DISPLAY_MODE_PER_LITER:
        return f"{_decimal_to_text(price_per_liter)} ₽ / л"
    price_per_100ml = (price_per_liter / Decimal("10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{_decimal_to_text(price_per_100ml)} ₽ / 100 мл"


def _normalize_etag(value: str | None) -> str:
    normalized = (value or "").strip()
    if normalized.startswith("W/"):
        normalized = normalized[2:]
    if len(normalized) >= 2 and normalized[0] == normalized[-1] == '"':
        normalized = normalized[1:-1]
    return normalized


def _asset_url(asset_id: uuid.UUID) -> str:
    return f"/api/media-assets/{asset_id}/content"


def serialize_media_asset(
    asset: models.MediaAsset,
    *,
    content_url: Optional[str] = None,
) -> schemas.MediaAssetListItem:
    return schemas.MediaAssetListItem(
        asset_id=asset.asset_id,
        kind=asset.kind,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        byte_size=asset.byte_size,
        width=asset.width,
        height=asset.height,
        checksum_sha256=asset.checksum_sha256,
        content_url=content_url or _asset_url(asset.asset_id),
        created_at=asset.created_at,
    )


def serialize_created_media_asset(
    asset: models.MediaAsset,
    *,
    content_url: Optional[str] = None,
) -> schemas.MediaAssetCreateResponse:
    return schemas.MediaAssetCreateResponse(
        asset_id=asset.asset_id,
        kind=asset.kind,
        storage_key=asset.storage_key,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        byte_size=asset.byte_size,
        width=asset.width,
        height=asset.height,
        checksum_sha256=asset.checksum_sha256,
        content_url=content_url or _asset_url(asset.asset_id),
        created_at=asset.created_at,
    )


def get_media_asset(db: Session, asset_id: uuid.UUID) -> models.MediaAsset:
    asset = db.query(models.MediaAsset).filter(models.MediaAsset.asset_id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    return asset


def list_media_assets(db: Session, *, kind: Optional[str] = None) -> list[models.MediaAsset]:
    query = db.query(models.MediaAsset)
    if kind:
        query = query.filter(models.MediaAsset.kind == kind)
    return query.order_by(models.MediaAsset.created_at.desc()).all()


def create_media_asset(
    db: Session,
    *,
    asset_id: Optional[uuid.UUID] = None,
    kind: str,
    original_filename: str,
    mime_type: str,
    storage_key: str,
    byte_size: int,
    checksum_sha256: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> models.MediaAsset:
    asset = models.MediaAsset(
        asset_id=asset_id or uuid.uuid4(),
        kind=normalize_media_kind(kind),
        original_filename=original_filename,
        mime_type=mime_type,
        storage_key=storage_key,
        byte_size=byte_size,
        checksum_sha256=checksum_sha256,
        width=width,
        height=height,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _tap_with_display_relations(db: Session, tap_id: int) -> models.Tap:
    tap = (
        db.query(models.Tap)
        .options(
            joinedload(models.Tap.keg)
            .joinedload(models.Keg.beverage)
            .joinedload(models.Beverage.background_asset),
            joinedload(models.Tap.keg)
            .joinedload(models.Keg.beverage)
            .joinedload(models.Beverage.logo_asset),
            joinedload(models.Tap.display_config).joinedload(models.TapDisplayConfig.override_background_asset),
        )
        .filter(models.Tap.tap_id == tap_id)
        .first()
    )
    if tap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tap not found")
    return tap


def get_tap_display_config(db: Session, tap_id: int) -> schemas.TapDisplayConfig:
    tap = _tap_with_display_relations(db, tap_id)
    config = tap.display_config
    if config is None:
        return schemas.TapDisplayConfig(
            tap_id=tap.tap_id,
            enabled=True,
            idle_instruction=None,
            fallback_title=None,
            fallback_subtitle=None,
            maintenance_title=None,
            maintenance_subtitle=None,
            override_accent_color=None,
            override_background_asset_id=None,
            show_price_mode=None,
            updated_at=_now_utc(),
        )
    return schemas.TapDisplayConfig.model_validate(config)


def upsert_tap_display_config(
    db: Session,
    *,
    tap_id: int,
    payload: schemas.TapDisplayConfigUpsert,
) -> models.TapDisplayConfig:
    tap = _tap_with_display_relations(db, tap_id)
    config = tap.display_config
    if config is None:
        config = models.TapDisplayConfig(tap_id=tap.tap_id)
        db.add(config)

    for key, value in payload.model_dump().items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


def _snapshot_asset(
    asset: Optional[models.MediaAsset],
    *,
    content_url_builder: Optional[Callable[[uuid.UUID], str]] = None,
) -> Optional[schemas.DisplaySnapshotAsset]:
    if asset is None:
        return None
    if not storage_path_exists(asset.storage_key):
        LOGGER.warning("Skipping missing display asset asset_id=%s storage_key=%s", asset.asset_id, asset.storage_key)
        return None
    url_builder = content_url_builder or (lambda asset_id: _asset_url(asset_id))
    return schemas.DisplaySnapshotAsset(
        asset_id=asset.asset_id,
        kind=asset.kind,
        checksum_sha256=asset.checksum_sha256,
        content_url=url_builder(asset.asset_id),
        width=asset.width,
        height=asset.height,
    )


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_display_snapshot(
    db: Session,
    *,
    tap_id: int,
    content_url_builder: Optional[Callable[[uuid.UUID], str]] = None,
) -> schemas.DisplayTapSnapshot:
    tap = _tap_with_display_relations(db, tap_id)
    config = tap.display_config
    beverage = tap.keg.beverage if tap.keg and tap.keg.beverage else None

    emergency_stop_state = system_crud.get_state(db, EMERGENCY_STOP_KEY, "false")
    emergency_stop = str(emergency_stop_state.value).strip().lower() == "true"

    display_mode = _resolve_price_mode(
        config.show_price_mode if config else None,
        beverage.price_display_mode_default if beverage else None,
    )

    theme_background_asset = (
        config.override_background_asset if config and config.override_background_asset else None
    ) or (beverage.background_asset if beverage else None)
    logo_asset = beverage.logo_asset if beverage else None

    snapshot_payload = {
        "tap": {
            "tap_id": tap.tap_id,
            "display_name": tap.display_name,
            "status": tap.status,
            "enabled": config.enabled if config else True,
        },
        "service_flags": {
            "emergency_stop": emergency_stop,
        },
        "assignment": {
            "keg_id": tap.keg.keg_id if tap.keg else None,
            "beverage_id": beverage.beverage_id if beverage else None,
            "has_assignment": beverage is not None,
        },
        "presentation": {
            "name": beverage.name if beverage else None,
            "brand_name": (beverage.display_brand_name or beverage.brewery) if beverage else None,
            "brewery": beverage.brewery if beverage else None,
            "style": beverage.style if beverage else None,
            "abv": beverage.abv if beverage else None,
            "description_short": beverage.description_short if beverage else None,
        },
        "pricing": {
            "sell_price_per_liter": beverage.sell_price_per_liter if beverage else None,
            "price_per_100ml_cents": _price_per_100ml_cents(beverage.sell_price_per_liter) if beverage else None,
            "display_mode": display_mode,
            "display_text": _format_price_display(beverage.sell_price_per_liter if beverage else None, display_mode),
        },
        "theme": {
            "accent_color": (
                config.override_accent_color if config and config.override_accent_color else None
            ) or (beverage.accent_color if beverage and beverage.accent_color else None) or DEFAULT_ACCENT_COLOR,
            "text_theme": (beverage.text_theme if beverage and beverage.text_theme else None) or DEFAULT_TEXT_THEME,
            "background_asset": _snapshot_asset(theme_background_asset, content_url_builder=content_url_builder),
            "logo_asset": _snapshot_asset(logo_asset, content_url_builder=content_url_builder),
        },
        "copy_block": {
            "idle_instruction": config.idle_instruction if config and config.idle_instruction else DEFAULT_IDLE_INSTRUCTION,
            "fallback_title": config.fallback_title if config and config.fallback_title else DEFAULT_FALLBACK_TITLE,
            "fallback_subtitle": (
                config.fallback_subtitle if config and config.fallback_subtitle else DEFAULT_FALLBACK_SUBTITLE
            ),
            "maintenance_title": (
                config.maintenance_title if config and config.maintenance_title else DEFAULT_MAINTENANCE_TITLE
            ),
            "maintenance_subtitle": (
                config.maintenance_subtitle if config and config.maintenance_subtitle else DEFAULT_MAINTENANCE_SUBTITLE
            ),
        },
    }

    content_version = hashlib.sha256(_canonical_json(snapshot_payload).encode("utf-8")).hexdigest()
    generated_at = _now_utc()

    return schemas.DisplayTapSnapshot(
        **snapshot_payload,
        content_version=content_version,
        generated_at=generated_at,
    )


def is_not_modified(if_none_match: Optional[str], *, current_content_version: str) -> bool:
    if not if_none_match:
        return False
    current = _normalize_etag(current_content_version)
    provided_values = {_normalize_etag(value) for value in if_none_match.split(",")}
    return current in provided_values
