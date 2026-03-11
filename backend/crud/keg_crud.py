import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from crud import beverage_crud


def get_keg(db: Session, keg_id: uuid.UUID):
    db_keg = (
        db.query(models.Keg)
        .options(joinedload(models.Keg.beverage))
        .filter(models.Keg.keg_id == keg_id)
        .first()
    )
    if db_keg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keg not found")
    return db_keg


def get_kegs(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Keg)
        .options(joinedload(models.Keg.beverage))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_fifo_candidate_kegs(db: Session, beer_type_id: uuid.UUID):
    candidates = (
        db.query(models.Keg)
        .options(joinedload(models.Keg.beverage))
        .outerjoin(models.Tap, models.Tap.keg_id == models.Keg.keg_id)
        .filter(
            models.Keg.beverage_id == beer_type_id,
            models.Keg.status == "full",
            models.Keg.current_volume_ml > 0,
            models.Tap.tap_id.is_(None),
        )
        .all()
    )
    return sorted(
        candidates,
        key=lambda keg: (
            keg.created_at or datetime.min.replace(tzinfo=timezone.utc),
            str(keg.keg_id),
        ),
    )


def get_fifo_suggestion(db: Session, beer_type_id: uuid.UUID) -> schemas.KegSuggestionResponse:
    candidates = get_fifo_candidate_kegs(db=db, beer_type_id=beer_type_id)
    recommended = candidates[0] if candidates else None
    return schemas.KegSuggestionResponse(
        recommended_keg=recommended,
        candidates_count=len(candidates),
        reason="oldest_available" if recommended else "no_available_kegs",
        ordering_keys_used=["created_at", "keg_id"],
    )


def create_keg(db: Session, keg: schemas.KegCreate):
    beverage_crud.get_beverage(db, beverage_id=keg.beverage_id)

    db_keg = models.Keg(
        beverage_id=keg.beverage_id,
        initial_volume_ml=keg.initial_volume_ml,
        purchase_price=keg.purchase_price,
        current_volume_ml=keg.initial_volume_ml,
    )

    db.add(db_keg)
    db.commit()
    db.refresh(db_keg)
    return db_keg


def update_keg(db: Session, keg_id: uuid.UUID, keg_update: schemas.KegUpdate):
    db_keg = get_keg(db, keg_id=keg_id)
    update_data = keg_update.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "in_use" and db_keg.tapped_at is None:
            db_keg.tapped_at = func.now()
        elif new_status == "empty" and db_keg.finished_at is None:
            db_keg.finished_at = func.now()

    for key, value in update_data.items():
        setattr(db_keg, key, value)

    db.commit()
    db.refresh(db_keg)
    return db_keg


def delete_keg(db: Session, keg_id: uuid.UUID):
    db_keg = get_keg(db, keg_id=keg_id)
    if db_keg.status == "in_use":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete keg {keg_id} because it is currently in use.",
        )

    db.delete(db_keg)
    db.commit()
    return db_keg
