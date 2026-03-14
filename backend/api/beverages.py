# backend/api/beverages.py
from typing import List, Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import schemas
from crud import beverage_crud
from database import get_db
import security

router = APIRouter(
    prefix="/beverages",
    tags=["Beverages"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Beverage, status_code=201, summary="РЎРѕР·РґР°С‚СЊ РЅРѕРІС‹Р№ РЅР°РїРёС‚РѕРє")
def create_beverage(
    beverage: schemas.BeverageCreate, 
    db: Session = Depends(get_db)
):
    """
    РЎРѕР·РґР°РµС‚ РЅРѕРІСѓСЋ Р·Р°РїРёСЃСЊ Рѕ РЅР°РїРёС‚РєРµ РІ РіР»РѕР±Р°Р»СЊРЅРѕРј СЃРїСЂР°РІРѕС‡РЅРёРєРµ.

    РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РґР»СЏ РґРѕР±Р°РІР»РµРЅРёСЏ РЅРѕРІРѕРіРѕ РїРёРІР° РёР»Рё РґСЂСѓРіРѕРіРѕ РЅР°РїРёС‚РєР° РІ Р°СЃСЃРѕСЂС‚РёРјРµРЅС‚ Р±Р°СЂР°.
    РќР°Р·РІР°РЅРёРµ РЅР°РїРёС‚РєР° (`name`) РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ СѓРЅРёРєР°Р»СЊРЅС‹Рј.
    """
    return beverage_crud.create_beverage(db=db, beverage=beverage)

@router.get("/", response_model=List[schemas.Beverage], summary="РџРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РЅР°РїРёС‚РєРѕРІ")
def read_beverages(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… РЅР°РїРёС‚РєРѕРІ, Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅРЅС‹С… РІ СЃРёСЃС‚РµРјРµ,
    СЃ РїРѕРґРґРµСЂР¶РєРѕР№ РїР°РіРёРЅР°С†РёРё.
    """
    return beverage_crud.get_beverages(db, skip=skip, limit=limit)

@router.get("/{beverage_id}", response_model=schemas.Beverage, summary="РџРѕР»СѓС‡РёС‚СЊ РЅР°РїРёС‚РѕРє РїРѕ ID")
def read_beverage(
    beverage_id: uuid.UUID, # РРЎРџР РђР’Р›Р•РќРР•: РўРёРї ID РёР·РјРµРЅРµРЅ РЅР° UUID РІ СЃРѕРѕС‚РІРµС‚СЃС‚РІРёРё СЃ РјРѕРґРµР»СЊСЋ
    db: Session = Depends(get_db)
):
    """
    РџРѕР»СѓС‡Р°РµС‚ РґРµС‚Р°Р»СЊРЅСѓСЋ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ РєРѕРЅРєСЂРµС‚РЅРѕРј РЅР°РїРёС‚РєРµ РїРѕ РµРіРѕ СѓРЅРёРєР°Р»СЊРЅРѕРјСѓ РёРґРµРЅС‚РёС„РёРєР°С‚РѕСЂСѓ (UUID).
    """
    db_beverage = beverage_crud.get_beverage(db, beverage_id=beverage_id)
    # РћР±СЂР°Р±РѕС‚РєР° РѕС€РёР±РєРё 404 Not Found РІСЃС‚СЂРѕРµРЅР° РІ crud-С„СѓРЅРєС†РёСЋ
    return db_beverage

@router.put("/{beverage_id}", response_model=schemas.Beverage, summary="Update beverage")
def update_beverage(
    beverage_id: uuid.UUID,
    beverage_update: schemas.BeverageUpdate,
    db: Session = Depends(get_db)
):
    return beverage_crud.update_beverage(db=db, beverage_id=beverage_id, beverage_update=beverage_update)
