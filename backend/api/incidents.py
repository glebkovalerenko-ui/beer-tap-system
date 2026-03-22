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
