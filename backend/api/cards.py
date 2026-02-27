# backend/api/cards.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import schemas
import security
from crud import card_crud
from database import get_db


router = APIRouter(
    prefix="/cards",
    tags=["Cards"],
    dependencies=[Depends(security.get_current_user)],
)


@router.post("/", response_model=schemas.Card, status_code=status.HTTP_201_CREATED, summary="Register card")
def create_card(card: schemas.CardCreate, db: Session = Depends(get_db)):
    return card_crud.create_card(db=db, card=card)


@router.get("/", response_model=List[schemas.Card], summary="List cards")
def read_cards(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return card_crud.get_cards(db, skip=skip, limit=limit)


@router.get("/{card_uid}/resolve", response_model=schemas.CardResolveResponse, summary="Resolve card state by UID")
def resolve_card(card_uid: str, db: Session = Depends(get_db)):
    return card_crud.resolve_card(db=db, card_uid=card_uid)


@router.put("/{card_uid}/status", response_model=schemas.Card, summary="Update card status")
def update_card_status(card_uid: str, card_update: schemas.CardStatusUpdate, db: Session = Depends(get_db)):
    db_card = card_crud.update_card_status(db, card_uid=card_uid, new_status=card_update.status)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return db_card
