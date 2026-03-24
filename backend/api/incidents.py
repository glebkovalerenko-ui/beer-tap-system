import os
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import schemas
import security
from crud import incident_crud
from database import get_db

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


def _build_capability(*, enabled: bool, reason: str | None = None) -> schemas.IncidentMutationCapability:
    return schemas.IncidentMutationCapability(enabled=enabled, reason=reason if not enabled else None)


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
        escalate=_build_capability(enabled=True),
        close=_build_capability(enabled=True),
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
    return incident_crud.claim_incident(db, incident_id=incident_id, owner=payload.owner.strip(), note=payload.note, actor_id=str(actor_id) if actor_id else None)


@router.post("/{incident_id}/notes", response_model=schemas.IncidentListItem, summary="Добавить заметку к инциденту")
def add_incident_note(
    incident_id: str,
    payload: schemas.IncidentNotePayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    return incident_crud.add_note(db, incident_id=incident_id, note=payload.note.strip(), actor_id=str(actor_id) if actor_id else None)


@router.post("/{incident_id}/escalate", response_model=schemas.IncidentListItem, summary="Эскалировать инцидент")
def escalate_incident(
    incident_id: str,
    payload: schemas.IncidentEscalationPayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    return incident_crud.escalate_incident(db, incident_id=incident_id, reason=payload.reason.strip(), note=payload.note.strip() if payload.note else None, actor_id=str(actor_id) if actor_id else None)


@router.post("/{incident_id}/close", response_model=schemas.IncidentListItem, summary="Закрыть инцидент")
def close_incident(
    incident_id: str,
    payload: schemas.IncidentClosePayload,
    _permission_guard: Annotated[dict, Depends(security.require_permissions("incidents_manage"))],
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = (current_user or {}).get("username")
    return incident_crud.close_incident(db, incident_id=incident_id, resolution_summary=payload.resolution_summary.strip(), note=payload.note.strip() if payload.note else None, actor_id=str(actor_id) if actor_id else None)
