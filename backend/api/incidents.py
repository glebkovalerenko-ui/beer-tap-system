import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import schemas
import security
from crud import incident_crud
from database import get_db
from operator_stream import operator_stream_hub

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
    dependencies=[Depends(security.get_current_user)],
)


ROLE_LABELS = {
    "operator": "Оператор",
    "shift_lead": "Старший смены",
    "engineer_owner": "Инженер / владелец",
}


def _flag_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _build_capability(
    *,
    enabled: bool,
    reason: str | None = None,
    confirm_required: bool = False,
    second_approval_required: bool = False,
    reason_code_required: bool = False,
) -> schemas.IncidentMutationCapability:
    disabled_reason = reason if not enabled else None
    return schemas.IncidentMutationCapability(
        enabled=enabled,
        reason=disabled_reason,
        allowed=enabled,
        confirm_required=confirm_required,
        second_approval_required=second_approval_required,
        reason_code_required=reason_code_required,
        disabled_reason=disabled_reason,
    )


def _incident_capabilities(current_user: dict | None) -> schemas.IncidentMutationCapabilities:
    role = (current_user or {}).get("role") or "operator"
    role_label = ROLE_LABELS.get(role, role)
    permissions = {
        str(item).strip()
        for item in (current_user or {}).get("permissions", [])
        if str(item).strip()
    }

    if "incidents_manage" not in permissions:
        reason = f"Эскалация недоступна для роли {role_label}."
        return schemas.IncidentMutationCapabilities(
            claim=_build_capability(enabled=False, reason=reason),
            note=_build_capability(enabled=False, reason=reason),
            escalate=_build_capability(enabled=False, reason=reason),
            close=_build_capability(enabled=False, reason=reason),
        )

    if not _flag_enabled("INCIDENT_MUTATION_ENDPOINTS_ENABLED", default=True):
        reason = "Endpoint временно отключён."
        return schemas.IncidentMutationCapabilities(
            claim=_build_capability(enabled=False, reason=reason),
            note=_build_capability(enabled=False, reason=reason),
            escalate=_build_capability(enabled=False, reason=reason),
            close=_build_capability(enabled=False, reason=reason),
        )

    return schemas.IncidentMutationCapabilities(
        claim=_build_capability(enabled=True),
        note=_build_capability(enabled=True),
        escalate=_build_capability(enabled=True, confirm_required=True, reason_code_required=True),
        close=_build_capability(enabled=True, confirm_required=True, reason_code_required=True),
    )


@router.get("/", response_model=schemas.IncidentListResponse, summary="Получить агрегированный список инцидентов")
def read_incidents(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    return schemas.IncidentListResponse(
        items=incident_crud.list_incidents(db, limit=limit),
        mutation_capabilities=_incident_capabilities(current_user),
        severity_matrix=incident_crud.severity_matrix_rows(),
    )


@router.post("/{incident_id}/claim", response_model=schemas.IncidentListItem, summary="Назначить owner и взять инцидент в работу")
def claim_incident(
    incident_id: str,
    payload: schemas.IncidentClaimPayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    incident = incident_crud.claim_incident(db, incident_id=incident_id, owner=payload.owner.strip(), note=payload.note, actor_id=str(actor_id) if actor_id else None)
    operator_stream_hub.emit_invalidation(resource="incident", entity_id=incident_id, reason="incident_claim")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=incident_id, reason="incident_claim")
    operator_stream_hub.emit_invalidation(resource="system", entity_id=incident_id, reason="incident_claim")
    return incident


@router.post("/{incident_id}/notes", response_model=schemas.IncidentListItem, summary="Добавить заметку к инциденту")
def add_incident_note(
    incident_id: str,
    payload: schemas.IncidentNotePayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    incident = incident_crud.add_note(db, incident_id=incident_id, note=payload.note.strip(), actor_id=str(actor_id) if actor_id else None)
    operator_stream_hub.emit_invalidation(resource="incident", entity_id=incident_id, reason="incident_note")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=incident_id, reason="incident_note")
    return incident


@router.post("/{incident_id}/escalate", response_model=schemas.IncidentListItem, summary="Эскалировать инцидент")
def escalate_incident(
    incident_id: str,
    payload: schemas.IncidentEscalationPayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    incident = incident_crud.escalate_incident(db, incident_id=incident_id, reason=payload.reason.strip(), note=payload.note.strip() if payload.note else None, actor_id=str(actor_id) if actor_id else None)
    operator_stream_hub.emit_invalidation(resource="incident", entity_id=incident_id, severity="warning", reason="incident_escalate")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=incident_id, severity="warning", reason="incident_escalate")
    operator_stream_hub.emit_invalidation(resource="system", entity_id=incident_id, severity="warning", reason="incident_escalate")
    return incident


@router.post("/{incident_id}/close", response_model=schemas.IncidentListItem, summary="Закрыть инцидент")
def close_incident(
    incident_id: str,
    payload: schemas.IncidentClosePayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    role = (current_user or {}).get("role") or "operator"
    incident = incident_crud.get_incident(db, incident_id)
    if not incident_crud.can_role_close_incident(incident, role):
        allowed = ", ".join(incident.get("role_gate_close") or [])
        raise HTTPException(status_code=403, detail=f"Close недоступен для роли {role}. Разрешено: {allowed}")
    updated_incident = incident_crud.close_incident(db, incident_id=incident_id, resolution_summary=payload.resolution_summary.strip(), note=payload.note.strip() if payload.note else None, actor_id=str(actor_id) if actor_id else None)
    operator_stream_hub.emit_invalidation(resource="incident", entity_id=incident_id, reason="incident_close")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=incident_id, reason="incident_close")
    operator_stream_hub.emit_invalidation(resource="system", entity_id=incident_id, reason="incident_close")
    return updated_incident
