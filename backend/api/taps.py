# backend/api/taps.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import schemas, security
from crud import display_crud, tap_crud
from database import get_db

router = APIRouter(
    prefix="/taps",
    tags=["Taps"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Tap, status_code=status.HTTP_201_CREATED, summary="Р”РѕР±Р°РІРёС‚СЊ РЅРѕРІС‹Р№ РєСЂР°РЅ")
def create_tap(tap: schemas.TapCreate, db: Session = Depends(get_db)):
    """
    Р”РѕР±Р°РІР»СЏРµС‚ РЅРѕРІС‹Р№ С„РёР·РёС‡РµСЃРєРёР№ РєСЂР°РЅ РІ СЃРёСЃС‚РµРјСѓ.
    РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ СЃРѕР·РґР°РµС‚СЃСЏ СЃРѕ СЃС‚Р°С‚СѓСЃРѕРј 'locked' (Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ).
    """
    return tap_crud.create_tap(db=db, tap=tap)

@router.get("/", response_model=List[schemas.Tap], summary="РџРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РІСЃРµС… РєСЂР°РЅРѕРІ")
def read_taps(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… РєСЂР°РЅРѕРІ.
    РћС‚РІРµС‚ РІРєР»СЋС‡Р°РµС‚ РїРѕР»РЅСѓСЋ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ РїРѕРґРєР»СЋС‡РµРЅРЅС‹С… РєРµРіР°С… Рё РёС… РЅР°РїРёС‚РєР°С…
    Р±Р»Р°РіРѕРґР°СЂСЏ "Р¶Р°РґРЅРѕР№ Р·Р°РіСЂСѓР·РєРµ" (eager loading).
    """
    return tap_crud.get_taps(db, skip=skip, limit=limit)

@router.get("/{tap_id}", response_model=schemas.Tap, summary="РџРѕР»СѓС‡РёС‚СЊ РєСЂР°РЅ РїРѕ ID")
def read_tap(tap_id: int, db: Session = Depends(get_db)):
    """
    РџРѕР»СѓС‡Р°РµС‚ РґРµС‚Р°Р»СЊРЅСѓСЋ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ РєРѕРЅРєСЂРµС‚РЅРѕРј РєСЂР°РЅРµ РїРѕ РµРіРѕ ID.
    """
    return tap_crud.get_tap(db, tap_id=tap_id)

@router.put("/{tap_id}", response_model=schemas.Tap, summary="РћР±РЅРѕРІРёС‚СЊ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ РєСЂР°РЅРµ")
def update_tap(tap_id: int, tap_update: schemas.TapUpdate, db: Session = Depends(get_db)):
    """
    РћР±РЅРѕРІР»СЏРµС‚ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ РєСЂР°РЅРµ (РЅР°РїСЂРёРјРµСЂ, РµРіРѕ РѕС‚РѕР±СЂР°Р¶Р°РµРјРѕРµ РёРјСЏ РёР»Рё СЃС‚Р°С‚СѓСЃ).
    """
    return tap_crud.update_tap(db=db, tap_id=tap_id, tap_update=tap_update)

@router.delete("/{tap_id}", status_code=status.HTTP_204_NO_CONTENT, summary="РЈРґР°Р»РёС‚СЊ РєСЂР°РЅ")
def delete_tap(tap_id: int, db: Session = Depends(get_db)):
    """
    РЈРґР°Р»СЏРµС‚ РєСЂР°РЅ РёР· СЃРёСЃС‚РµРјС‹.

    **Р‘РёР·РЅРµСЃ-РїСЂР°РІРёР»Рѕ:** Р—Р°РїСЂРµС‰РµРЅРѕ СѓРґР°Р»СЏС‚СЊ РєСЂР°РЅ, Рє РєРѕС‚РѕСЂРѕРјСѓ РІ РґР°РЅРЅС‹Р№ РјРѕРјРµРЅС‚
    РїРѕРґРєР»СЋС‡РµРЅР° РєРµРіР°.
    """
    tap_crud.delete_tap(db=db, tap_id=tap_id)
    return # Р’РѕР·РІСЂР°С‰Р°РµРј 204 No Content

@router.put("/{tap_id}/keg", response_model=schemas.Tap, summary="РќР°Р·РЅР°С‡РёС‚СЊ РєРµРіСѓ РЅР° РєСЂР°РЅ")
def assign_keg(tap_id: int, assignment: schemas.TapAssignKeg, db: Session = Depends(get_db)):
    """
    РџСЂРёРІСЏР·С‹РІР°РµС‚ СѓРєР°Р·Р°РЅРЅСѓСЋ РєРµРіСѓ Рє РєСЂР°РЅСѓ.

    **Р‘РёР·РЅРµСЃ-Р»РѕРіРёРєР°:**
    - РџСЂРѕРІРµСЂСЏРµС‚, С‡С‚Рѕ РєСЂР°РЅ СЃРІРѕР±РѕРґРµРЅ (СЃС‚Р°С‚СѓСЃ 'locked').
    - РџСЂРѕРІРµСЂСЏРµС‚, С‡С‚Рѕ РєРµРіР° РіРѕС‚РѕРІР° Рє РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЋ (СЃС‚Р°С‚СѓСЃ 'full').
    - Р­РЅРґРїРѕРёРЅС‚ РёРґРµРјРїРѕС‚РµРЅС‚РµРЅ.

    **РџРѕР±РѕС‡РЅС‹Рµ СЌС„С„РµРєС‚С‹:**
    - РЎС‚Р°С‚СѓСЃ РєСЂР°РЅР° -> 'active'.
    - РЎС‚Р°С‚СѓСЃ РєРµРіРё -> 'in_use'.
    """
    return tap_crud.assign_keg_to_tap(db=db, tap_id=tap_id, keg_id=assignment.keg_id)

@router.delete("/{tap_id}/keg", response_model=schemas.Tap, summary="РЎРЅСЏС‚СЊ РєРµРіСѓ СЃ РєСЂР°РЅР°")
def unassign_keg(tap_id: int, db: Session = Depends(get_db)):
    """
    РЎРЅРёРјР°РµС‚ С‚РµРєСѓС‰СѓСЋ РєРµРіСѓ СЃ РєСЂР°РЅР°.

    **РџРѕР±РѕС‡РЅС‹Рµ СЌС„С„РµРєС‚С‹:**
    - РЎС‚Р°С‚СѓСЃ РєСЂР°РЅР° -> 'locked'.
    - РЎС‚Р°С‚СѓСЃ РєРµРіРё -> 'full' (РµСЃР»Рё РѕРЅР° РЅРµ Р±С‹Р»Р° РїСѓСЃС‚РѕР№).
    """
    return tap_crud.unassign_keg_from_tap(db=db, tap_id=tap_id)


@router.get("/{tap_id}/display-config", response_model=schemas.TapDisplayConfig, summary="Get tap display config")
def read_tap_display_config(tap_id: int, db: Session = Depends(get_db)):
    return display_crud.get_tap_display_config(db=db, tap_id=tap_id)


@router.put("/{tap_id}/display-config", response_model=schemas.TapDisplayConfig, summary="Update tap display config")
def update_tap_display_config(
    tap_id: int,
    tap_display_config: schemas.TapDisplayConfigUpsert,
    db: Session = Depends(get_db),
):
    config = display_crud.upsert_tap_display_config(db=db, tap_id=tap_id, payload=tap_display_config)
    return schemas.TapDisplayConfig.model_validate(config)
