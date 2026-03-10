# backend/api/controllers.py
import json
from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
import security
from crud import controller_crud
from database import get_db

router = APIRouter(
    prefix="/controllers",
    tags=["Controllers"]
)


@router.post("/register", response_model=schemas.Controller, summary="Зарегистрировать контроллер (check-in)")
def register_controller(
    controller: schemas.ControllerRegister,
    db: Session = Depends(get_db)
):
    return controller_crud.register_controller(db=db, controller=controller)


@router.get("/", response_model=List[schemas.Controller], summary="Получить список контроллеров")
def read_controllers(
    current_user: Annotated[schemas.Guest, Depends(security.get_current_user)],
    db: Session = Depends(get_db)
):
    return controller_crud.get_controllers(db)


@router.post(
    "/flow-events",
    response_model=schemas.ControllerFlowEventResponse,
    status_code=202,
    summary="Report controller flow anomaly",
)
def report_flow_event(
    payload: schemas.ControllerFlowEventRequest,
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
    db: Session = Depends(get_db),
):
    db.add(
        models.AuditLog(
            actor_id=(current_user or {}).get("username", "internal_rpi"),
            action="controller_flow_anomaly",
            target_entity="Tap",
            target_id=str(payload.tap_id),
            details=json.dumps(
                {
                    "tap_id": payload.tap_id,
                    "volume_ml": payload.volume_ml,
                    "duration_ms": payload.duration_ms,
                    "card_present": payload.card_present,
                    "session_state": payload.session_state,
                    "reason": payload.reason,
                },
                ensure_ascii=False,
            ),
        )
    )
    db.commit()
    return schemas.ControllerFlowEventResponse(accepted=True)
