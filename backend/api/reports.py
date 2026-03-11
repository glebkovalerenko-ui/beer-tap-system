from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import schemas
import security
from crud import flow_accounting_crud
from database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.get(
    "/flow-summary",
    response_model=schemas.FlowSummaryResponse,
    summary="Get sale vs non-sale vs total flow summary",
)
def get_flow_summary(
    tap_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: Annotated[dict, Depends(security.get_current_user)] = None,
):
    return flow_accounting_crud.get_flow_summary(db=db, tap_id=tap_id)
