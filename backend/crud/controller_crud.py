# backend/crud/controller_crud.py
import json
from datetime import timedelta

from sqlalchemy.orm import Session

import models
import schemas
from crud import flow_accounting_crud

def get_controllers(db: Session):
    """Возвращает список всех зарегистрированных контроллеров."""
    return db.query(models.Controller).all()

def register_controller(db: Session, controller: schemas.ControllerRegister) -> models.Controller:
    """
    Регистрирует или обновляет информацию о контроллере.
    Это реализация логики "upsert".
    """
    # 1. Пытаемся найти существующий контроллер по ID
    db_controller = db.query(models.Controller).filter(models.Controller.controller_id == controller.controller_id).first()

    if db_controller:
        # 2. Если контроллер найден - обновляем его данные
        db_controller.ip_address = controller.ip_address
        db_controller.firmware_version = controller.firmware_version
        # Поле `last_seen` обновится автоматически благодаря `onupdate` в модели
    else:
        # 3. Если контроллер не найден - создаем новую запись
        db_controller = models.Controller(**controller.dict())
        db.add(db_controller)
    
    # 4. Сохраняем изменения в БД
    db.commit()
    db.refresh(db_controller)
    return db_controller


def record_flow_event(
    db: Session,
    *,
    payload: schemas.ControllerFlowEventRequest,
    actor_id: str,
) -> None:
    db.add(
        models.AuditLog(
            actor_id=actor_id,
            action="controller_flow_event",
            target_entity="Tap",
            target_id=str(payload.tap_id),
            details=json.dumps(
                {
                    "event_id": payload.event_id,
                    "event_status": payload.event_status,
                    "tap_id": payload.tap_id,
                    "volume_ml": payload.volume_ml,
                    "duration_ms": payload.duration_ms,
                    "card_present": payload.card_present,
                    "valve_open": payload.valve_open,
                    "session_state": payload.session_state,
                    "card_uid": payload.card_uid,
                    "short_id": payload.short_id,
                    "reason": payload.reason,
                },
                ensure_ascii=False,
            ),
        )
    )
    if flow_accounting_crud.is_non_sale_flow_event(payload):
        flow_accounting_crud.record_non_sale_flow(db=db, payload=payload)


def get_latest_flow_events(db: Session, limit: int = 20) -> list[dict]:
    rows = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action == "controller_flow_event")
        .order_by(models.AuditLog.timestamp.desc())
        .limit(max(int(limit or 20) * 10, 100))
        .all()
    )

    status_rank = {"started": 0, "updated": 1, "stopped": 2}
    latest_by_event_id: dict[str, tuple[models.AuditLog, dict, str]] = {}
    tap_ids: set[int] = set()

    for row in rows:
        try:
            details = json.loads(row.details or "{}")
        except json.JSONDecodeError:
            details = {}

        event_id = str(details.get("event_id") or row.log_id)
        tap_id = int(details.get("tap_id") or 0)
        candidate = (row, details, event_id)
        current = latest_by_event_id.get(event_id)

        if current is None:
            latest_by_event_id[event_id] = candidate
            tap_ids.add(tap_id)
            continue

        current_row, current_details, _ = current
        current_duration_ms = int(current_details.get("duration_ms") or 0)
        candidate_duration_ms = int(details.get("duration_ms") or 0)
        current_status_rank = status_rank.get(str(current_details.get("event_status") or "updated"), 1)
        candidate_status_rank = status_rank.get(str(details.get("event_status") or "updated"), 1)

        if (
            row.timestamp > current_row.timestamp
            or (row.timestamp == current_row.timestamp and candidate_duration_ms > current_duration_ms)
            or (
                row.timestamp == current_row.timestamp
                and candidate_duration_ms == current_duration_ms
                and candidate_status_rank > current_status_rank
            )
        ):
            latest_by_event_id[event_id] = candidate
            tap_ids.add(tap_id)

    latest_rows = sorted(
        latest_by_event_id.values(),
        key=lambda item: (
            item[0].timestamp,
            int(item[1].get("duration_ms") or 0),
            status_rank.get(str(item[1].get("event_status") or "updated"), 1),
        ),
        reverse=True,
    )[:limit]

    taps = (
        db.query(models.Tap)
        .filter(models.Tap.tap_id.in_(tap_ids))
        .all()
        if tap_ids
        else []
    )
    tap_names = {tap.tap_id: tap.display_name for tap in taps}

    items: list[dict] = []
    for row, details, event_id in latest_rows:
        duration_ms = int(details.get("duration_ms") or 0)
        started_at = row.timestamp - timedelta(milliseconds=duration_ms) if duration_ms > 0 else None
        event_status = details.get("event_status") or "updated"
        tap_id = int(details.get("tap_id") or 0)
        items.append(
            {
                "item_id": event_id,
                "item_type": "flow_event",
                "status": "in_progress" if event_status in {"started", "updated"} else "stopped",
                "tap_id": tap_id,
                "tap_name": tap_names.get(tap_id),
                "timestamp": row.timestamp,
                "started_at": started_at,
                "ended_at": row.timestamp if event_status == "stopped" else None,
                "duration_ms": duration_ms,
                "volume_ml": int(details.get("volume_ml") or 0),
                "amount_charged": None,
                "short_id": details.get("short_id"),
                "guest": None,
                "beverage_name": None,
                "card_uid": details.get("card_uid"),
                "card_present": details.get("card_present"),
                "session_state": details.get("session_state"),
                "valve_open": details.get("valve_open"),
                "reason": details.get("reason"),
                "event_status": event_status,
            }
        )

    return items
