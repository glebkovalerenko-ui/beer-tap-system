from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models


SHIFT_CLOSE_BLOCK_ACTIVE_VISITS = "active_visits_exist"
SHIFT_CLOSE_BLOCK_PENDING_SYNC = "pending_sync_pours_exist"


def get_open_shift(db: Session):
    return (
        db.query(models.Shift)
        .filter(models.Shift.status == "open")
        .order_by(models.Shift.opened_at.desc())
        .first()
    )


def ensure_open_shift(db: Session):
    shift = get_open_shift(db)
    if not shift:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Shift is closed")
    return shift


def get_current_shift_state(db: Session):
    shift = get_open_shift(db)
    if not shift:
        return {"status": "closed", "shift": None}
    return {"status": "open", "shift": shift}


def open_shift(db: Session, opened_by: str | None):
    existing = get_open_shift(db)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shift already open")

    shift = models.Shift(
        status="open",
        opened_at=datetime.now(timezone.utc),
        opened_by=opened_by,
    )
    db.add(shift)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shift already open")

    db.refresh(shift)
    return shift


def close_shift(db: Session, closed_by: str | None):
    shift = get_open_shift(db)
    if not shift:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No open shift")

    active_visit = (
        db.query(models.Visit.visit_id)
        .filter(models.Visit.status == "active")
        .first()
    )
    if active_visit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=SHIFT_CLOSE_BLOCK_ACTIVE_VISITS,
        )

    pending_sync = (
        db.query(models.Pour.pour_id)
        .filter(models.Pour.sync_status == "pending_sync")
        .first()
    )
    if pending_sync:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=SHIFT_CLOSE_BLOCK_PENDING_SYNC,
        )

    shift.status = "closed"
    shift.closed_at = datetime.now(timezone.utc)
    shift.closed_by = closed_by
    db.commit()
    db.refresh(shift)
    return shift
