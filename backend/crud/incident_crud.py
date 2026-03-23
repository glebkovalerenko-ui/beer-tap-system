import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

import models

EMERGENCY_STOP_KEY = "emergency_stop_enabled"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _minutes_since(value: Optional[datetime]) -> Optional[int]:
    value = _as_utc(value)
    if value is None:
        return None
    now = _utcnow()
    return max(0, int((now - value).total_seconds() // 60))


def _device_health(state: str, label: str, detail: Optional[str] = None, updated_at: Optional[datetime] = None):
    return {
        "state": state,
        "label": label,
        "detail": detail,
        "updated_at": updated_at,
    }


def _priority_for_flow(reason: Optional[str]) -> str:
    critical = {
        "flow_detected_when_valve_closed_without_active_session",
        "flow_detected_with_no_card",
    }
    if reason in critical:
        return "high"
    return "medium"


def _type_label(reason: Optional[str]) -> str:
    mapping = {
        "flow_detected_when_valve_closed_without_active_session": "closed_valve_flow",
        "flow_detected_with_no_card": "non_sale_flow",
        "authorized_pour_in_progress": "authorized_flow",
    }
    return mapping.get(reason or "", reason or "operational_anomaly")


def _incident_action_detail(action: str, **details) -> str:
    payload = {"action": action, **{key: value for key, value in details.items() if value not in (None, "")}}
    return json.dumps(payload, ensure_ascii=False)


def _record_action_log(db: Session, *, incident_id: str, actor_id: Optional[str], action: str, details: dict) -> None:
    db.add(models.AuditLog(
        actor_id=actor_id,
        action=f"incident_{action}",
        target_entity="Incident",
        target_id=incident_id,
        details=_incident_action_detail(action, **details),
    ))


def _get_incident_state(db: Session, incident_id: str) -> Optional[models.IncidentState]:
    return db.query(models.IncidentState).filter(models.IncidentState.incident_id == incident_id).first()


def _get_or_create_incident_state(db: Session, incident: dict) -> models.IncidentState:
    state = _get_incident_state(db, incident["incident_id"])
    if state:
        return state
    state = models.IncidentState(
        incident_id=incident["incident_id"],
        status=incident["status"],
        owner=incident.get("operator"),
        last_action=incident.get("note_action"),
        last_action_at=incident.get("created_at"),
        last_note=incident.get("note_action"),
        escalated_at=None,
        escalation_reason=None,
        closed_at=incident.get("created_at") if incident["status"] == "closed" else None,
        closure_summary=incident.get("note_action") if incident["status"] == "closed" else None,
    )
    db.add(state)
    db.flush()
    return state


def _apply_overlay(base: dict, state: Optional[models.IncidentState]) -> dict:
    if not state:
        base.setdefault("owner", base.get("operator"))
        base.setdefault("last_action", base.get("note_action"))
        base.setdefault("last_action_at", base.get("created_at"))
        base.setdefault("escalated_at", None)
        base.setdefault("escalation_reason", None)
        base.setdefault("closed_at", base.get("created_at") if base.get("status") == "closed" else None)
        base.setdefault("closure_summary", base.get("note_action") if base.get("status") == "closed" else None)
        return base

    base["status"] = state.status or base["status"]
    base["operator"] = state.owner or base.get("operator")
    base["owner"] = state.owner or base.get("operator")
    base["note_action"] = state.last_note or state.last_action or base.get("note_action")
    base["last_action"] = state.last_action or state.last_note or base.get("note_action")
    base["last_action_at"] = state.last_action_at or base.get("created_at")
    base["escalated_at"] = state.escalated_at
    base["escalation_reason"] = state.escalation_reason
    base["closed_at"] = state.closed_at or (base.get("created_at") if base.get("status") == "closed" else None)
    base["closure_summary"] = state.closure_summary
    return base


def list_incidents(db: Session, limit: int = 100) -> list[dict]:
    incidents: list[dict] = []

    emergency_state = db.query(models.SystemState).filter(models.SystemState.key == EMERGENCY_STOP_KEY).first()
    if emergency_state and str(emergency_state.value).strip().lower() == "true":
        incidents.append({
            "incident_id": "system-emergency-stop",
            "priority": "critical",
            "created_at": datetime.now(timezone.utc),
            "tap": None,
            "type": "emergency_stop",
            "status": "in_progress",
            "operator": "system",
            "note_action": "Экстренная остановка активна. Возврат в normal mode должен быть подтверждён ответственным оператором.",
            "source": "system_state",
        })

    non_sale_rows = (
        db.query(models.NonSaleFlow)
        .options(joinedload(models.NonSaleFlow.tap))
        .order_by(models.NonSaleFlow.last_seen_at.desc())
        .limit(limit)
        .all()
    )
    for flow in non_sale_rows:
        incidents.append({
            "incident_id": f"flow-{flow.event_id}",
            "priority": _priority_for_flow(flow.reason),
            "created_at": flow.started_at or flow.created_at or flow.last_seen_at,
            "tap": flow.tap.display_name if flow.tap else f"Tap #{flow.tap_id}",
            "type": _type_label(flow.reason),
            "status": "closed" if flow.finalized_at else "in_progress",
            "operator": None,
            "note_action": f"Причина: {flow.reason}. Объём {flow.volume_ml} мл. Проверить кран #{flow.tap_id} и сверить действия оператора.",
            "source": "non_sale_flow",
        })

    audit_rows = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action.in_(["report_lost_card", "visit_force_unlock", "reconcile_pour"]))
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    for row in audit_rows:
        details = {}
        try:
            details = json.loads(row.details or "{}")
        except json.JSONDecodeError:
            details = {}
        incidents.append({
            "incident_id": f"audit-{row.log_id}",
            "priority": "medium",
            "created_at": row.timestamp,
            "tap": details.get("tap_name") or (f"Tap #{details.get('tap_id')}" if details.get("tap_id") else None),
            "type": row.action,
            "status": "closed" if row.action == "reconcile_pour" else "new",
            "operator": row.actor_id,
            "note_action": details.get("comment") or details.get("reason") or row.action,
            "source": "audit_log",
        })

    for tap in db.query(models.Tap).options(joinedload(models.Tap.keg)).all():
        if tap.keg_id is None:
            incidents.append({
                "incident_id": f"tap-no-keg-{tap.tap_id}",
                "priority": "medium",
                "created_at": _utcnow(),
                "tap": tap.display_name,
                "type": "tap_without_keg",
                "status": "new",
                "operator": None,
                "note_action": f"На {tap.display_name} не назначена кега. Назначьте кегу или переведите точку в maintenance.",
                "source": "tap_state",
            })

    incident_ids = [item["incident_id"] for item in incidents]
    overlays = {}
    if incident_ids:
        overlays = {row.incident_id: row for row in db.query(models.IncidentState).filter(models.IncidentState.incident_id.in_(incident_ids)).all()}

    incidents = [_apply_overlay(item, overlays.get(item["incident_id"])) for item in incidents]
    incidents.sort(key=lambda item: _as_utc(item["created_at"]) or _utcnow(), reverse=True)
    return incidents[:limit]


def get_incident(db: Session, incident_id: str) -> dict:
    for item in list_incidents(db, limit=500):
        if item["incident_id"] == incident_id:
            return item
    raise HTTPException(status_code=404, detail="Incident not found")


def claim_incident(db: Session, *, incident_id: str, owner: str, note: Optional[str], actor_id: Optional[str]) -> dict:
    incident = get_incident(db, incident_id)
    state = _get_or_create_incident_state(db, incident)
    now = _utcnow()
    state.owner = owner
    state.status = "closed" if state.closed_at else "in_progress"
    state.last_action = "claim"
    state.last_action_at = now
    state.last_note = note or f"Incident assigned to {owner}"
    _record_action_log(db, incident_id=incident_id, actor_id=actor_id, action="claim", details={"owner": owner, "note": note})
    db.commit()
    return get_incident(db, incident_id)


def add_note(db: Session, *, incident_id: str, note: str, actor_id: Optional[str]) -> dict:
    incident = get_incident(db, incident_id)
    state = _get_or_create_incident_state(db, incident)
    now = _utcnow()
    if state.status == "new":
        state.status = "in_progress" if state.owner else state.status
    state.last_action = "note"
    state.last_action_at = now
    state.last_note = note
    _record_action_log(db, incident_id=incident_id, actor_id=actor_id, action="note", details={"note": note})
    db.commit()
    return get_incident(db, incident_id)


def escalate_incident(db: Session, *, incident_id: str, reason: str, note: Optional[str], actor_id: Optional[str]) -> dict:
    incident = get_incident(db, incident_id)
    state = _get_or_create_incident_state(db, incident)
    now = _utcnow()
    if state.status != "closed":
        state.status = "in_progress"
    state.last_action = "escalate"
    state.last_action_at = now
    state.last_note = note or reason
    state.escalated_at = now
    state.escalation_reason = reason
    _record_action_log(db, incident_id=incident_id, actor_id=actor_id, action="escalate", details={"reason": reason, "note": note})
    db.commit()
    return get_incident(db, incident_id)


def close_incident(db: Session, *, incident_id: str, resolution_summary: str, note: Optional[str], actor_id: Optional[str]) -> dict:
    incident = get_incident(db, incident_id)
    state = _get_or_create_incident_state(db, incident)
    now = _utcnow()
    state.status = "closed"
    state.last_action = "close"
    state.last_action_at = now
    state.last_note = note or resolution_summary
    state.closed_at = now
    state.closure_summary = resolution_summary
    _record_action_log(db, incident_id=incident_id, actor_id=actor_id, action="close", details={"resolution_summary": resolution_summary, "note": note})
    db.commit()
    return get_incident(db, incident_id)


def get_system_summary(db: Session) -> dict:
    taps = db.query(models.Tap).options(joinedload(models.Tap.keg)).all()
    controllers = db.query(models.Controller).all()
    emergency_state = db.query(models.SystemState).filter(models.SystemState.key == EMERGENCY_STOP_KEY).first()
    emergency_stop = bool(emergency_state and str(emergency_state.value).strip().lower() == "true")
    open_non_sale = db.query(models.NonSaleFlow).filter(models.NonSaleFlow.finalized_at.is_(None)).count()
    open_incident_overlays = db.query(models.IncidentState).filter(models.IncidentState.status != "closed").count()
    pending_sync = db.query(models.Pour).filter(models.Pour.sync_status == "pending_sync").count()

    controller_devices = []
    for controller in controllers:
        stale_minutes = _minutes_since(controller.last_seen)
        state = "critical" if stale_minutes is None or stale_minutes >= 15 else "ok"
        controller_devices.append({
            "device_id": controller.controller_id,
            "device_type": "controller",
            "tap": None,
            "state": state,
            "label": controller.ip_address,
            "detail": f"last_seen {stale_minutes} min ago" if stale_minutes is not None else "no heartbeat",
            "updated_at": controller.last_seen,
        })

    display_devices = []
    reader_devices = []
    for tap in taps:
        display_state = "ok" if tap.keg_id else "warning"
        reader_state = "ok" if tap.status == "active" else "warning"
        display_devices.append({
            "device_id": f"display-{tap.tap_id}",
            "device_type": "display_agent",
            "tap": tap.display_name,
            "state": display_state,
            "label": "display assigned" if tap.keg_id else "waiting for keg",
            "detail": f"tap_status={tap.status}",
            "updated_at": None,
        })
        reader_devices.append({
            "device_id": f"reader-{tap.tap_id}",
            "device_type": "reader",
            "tap": tap.display_name,
            "state": reader_state,
            "label": "reader ready" if tap.status == "active" else "reader attention",
            "detail": f"tap_status={tap.status}",
            "updated_at": None,
        })

    def aggregate(name: str, devices: list[dict], *, ok_label: str):
        critical = sum(1 for item in devices if item["state"] == "critical")
        warning = sum(1 for item in devices if item["state"] == "warning")
        state = "critical" if critical else "warning" if warning else "ok"
        label = f"{len(devices)} devices" if devices else ok_label
        if name == "sync_queue":
            state = "critical" if pending_sync >= 10 else "warning" if pending_sync > 0 else "ok"
            label = f"{pending_sync} pending"
        return {"name": name, "state": state, "label": label, "detail": None, "devices": devices}

    backend_state = "critical" if emergency_stop else "warning" if open_non_sale else "ok"
    database_state = "warning" if pending_sync else "ok"

    subsystems = [
        {"name": "backend", "state": backend_state, "label": "emergency stop active" if emergency_stop else "backend online", "detail": f"open anomalies={open_non_sale}", "devices": []},
        {"name": "database", "state": database_state, "label": "sync backlog" if pending_sync else "db healthy", "detail": f"pending_sync={pending_sync}", "devices": []},
        aggregate("controllers", controller_devices, ok_label="no controllers registered"),
        aggregate("display_agents", display_devices, ok_label="no displays"),
        aggregate("readers", reader_devices, ok_label="no readers"),
        aggregate("sync_queue", [], ok_label="empty"),
    ]
    overall_state = "critical" if any(item["state"] == "critical" for item in subsystems) else "warning" if any(item["state"] == "warning" for item in subsystems) else "ok"
    return {
        "emergency_stop": emergency_stop,
        "overall_state": overall_state,
        "generated_at": _utcnow(),
        "open_incident_count": max(open_non_sale + (1 if emergency_stop else 0), open_incident_overlays),
        "subsystems": subsystems,
    }
