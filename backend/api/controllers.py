from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
    controller_crud.record_flow_event(
        db=db,
        payload=payload,
        actor_id=(current_user or {}).get("username", "internal_rpi"),
    )
    db.commit()
    return schemas.ControllerFlowEventResponse(accepted=True)
