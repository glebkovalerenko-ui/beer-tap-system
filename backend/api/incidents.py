from typing import Annotated, List

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


@router.get("/", response_model=List[schemas.IncidentListItem], summary="Получить агрегированный список инцидентов")
def read_incidents(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    return incident_crud.list_incidents(db, limit=limit)


@router.post("/{incident_id}/claim", response_model=schemas.IncidentListItem, summary="Назначить owner и взять инцидент в работу")
def claim_incident(
    incident_id: str,
    payload: schemas.IncidentClaimPayload,
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = getattr(current_user, "phone_number", None) or getattr(current_user, "guest_id", None)
    return incident_crud.claim_incident(db, incident_id=incident_id, owner=payload.owner.strip(), note=payload.note, actor_id=str(actor_id) if actor_id else None)


@router.post("/{incident_id}/notes", response_model=schemas.IncidentListItem, summary="Добавить заметку к инциденту")
def add_incident_note(
    incident_id: str,
    payload: schemas.IncidentNotePayload,
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = getattr(current_user, "phone_number", None) or getattr(current_user, "guest_id", None)
    return incident_crud.add_note(db, incident_id=incident_id, note=payload.note.strip(), actor_id=str(actor_id) if actor_id else None)


@router.post("/{incident_id}/escalate", response_model=schemas.IncidentListItem, summary="Эскалировать инцидент")
def escalate_incident(
    incident_id: str,
    payload: schemas.IncidentEscalationPayload,
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = getattr(current_user, "phone_number", None) or getattr(current_user, "guest_id", None)
    return incident_crud.escalate_incident(db, incident_id=incident_id, reason=payload.reason.strip(), note=payload.note.strip() if payload.note else None, actor_id=str(actor_id) if actor_id else None)


@router.post("/{incident_id}/close", response_model=schemas.IncidentListItem, summary="Закрыть инцидент")
def close_incident(
    incident_id: str,
    payload: schemas.IncidentClosePayload,
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    actor_id = getattr(current_user, "phone_number", None) or getattr(current_user, "guest_id", None)
    return incident_crud.close_incident(db, incident_id=incident_id, resolution_summary=payload.resolution_summary.strip(), note=payload.note.strip() if payload.note else None, actor_id=str(actor_id) if actor_id else None)
