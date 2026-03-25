from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import schemas, security
from crud import display_crud, tap_crud
from database import get_db
from operator_stream import operator_stream_hub

router = APIRouter(
    prefix="/taps",
    tags=["Taps"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Tap, status_code=status.HTTP_201_CREATED, summary="Добавить новый кран")
def create_tap(
    tap: schemas.TapCreate,
    _permission_guard: dict = Depends(security.require_permissions("settings_manage")),
    db: Session = Depends(get_db),
):
    """
    Добавляет новый физический кран в систему.
    По умолчанию создается со статусом 'locked' (заблокирован).
    """
    return tap_crud.create_tap(db=db, tap=tap)

@router.get("/", response_model=List[schemas.Tap], summary="Получить список всех кранов")
def read_taps(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Возвращает список всех кранов.
    Ответ включает полную информацию о подключенных кегах и их напитках
    благодаря "жадной загрузке" (eager loading).
    """
    return tap_crud.get_taps(db, skip=skip, limit=limit)

@router.get("/{tap_id}", response_model=schemas.Tap, summary="Получить кран по ID")
def read_tap(tap_id: int, db: Session = Depends(get_db)):
    """
    Получает детальную информацию о конкретном кране по его ID.
    """
    return tap_crud.get_tap(db, tap_id=tap_id)

@router.put("/{tap_id}", response_model=schemas.Tap, summary="Обновить информацию о кране")
def update_tap(
    tap_id: int,
    tap_update: schemas.TapUpdate,
    _permission_guard: dict = Depends(security.require_permissions("taps_control")),
    db: Session = Depends(get_db),
):
    """
    Обновляет информацию о кране (например, его отображаемое имя или статус).
    """
    tap = tap_crud.update_tap(db=db, tap_id=tap_id, tap_update=tap_update)
    operator_stream_hub.emit_invalidation(resource="taps", entity_id=str(tap_id), reason="tap_updated")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=str(tap_id), reason="tap_updated")
    operator_stream_hub.emit_invalidation(resource="system", entity_id=str(tap_id), reason="tap_updated")
    return tap

@router.delete("/{tap_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить кран")
def delete_tap(
    tap_id: int,
    _permission_guard: dict = Depends(security.require_permissions("settings_manage")),
    db: Session = Depends(get_db),
):
    """
    Удаляет кран из системы.

    **Бизнес-правило:** Запрещено удалять кран, к которому в данный момент
    подключена кега.
    """
    tap_crud.delete_tap(db=db, tap_id=tap_id)
    return # Возвращаем 204 No Content

@router.put("/{tap_id}/keg", response_model=schemas.Tap, summary="Назначить кегу на кран")
def assign_keg(
    tap_id: int,
    assignment: schemas.TapAssignKeg,
    _permission_guard: dict = Depends(security.require_permissions("taps_control")),
    db: Session = Depends(get_db),
):
    """
    Привязывает указанную кегу к крану.

    **Бизнес-логика:**
    - Проверяет, что кран свободен (статус 'locked').
    - Проверяет, что кега готова к использованию (статус 'full').
    - Эндпоинт идемпотентен.

    **Побочные эффекты:**
    - Статус крана -> 'active'.
    - Статус кеги -> 'in_use'.
    """
    tap = tap_crud.assign_keg_to_tap(db=db, tap_id=tap_id, keg_id=assignment.keg_id)
    operator_stream_hub.emit_invalidation(resource="taps", entity_id=str(tap_id), reason="tap_assign_keg")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=str(tap_id), reason="tap_assign_keg")
    operator_stream_hub.emit_invalidation(resource="system", entity_id=str(tap_id), reason="tap_assign_keg")
    return tap

@router.delete("/{tap_id}/keg", response_model=schemas.Tap, summary="Снять кегу с крана")
def unassign_keg(
    tap_id: int,
    _permission_guard: dict = Depends(security.require_permissions("taps_control")),
    db: Session = Depends(get_db),
):
    """
    Снимает текущую кегу с крана.

    **Побочные эффекты:**
    - Статус крана -> 'locked'.
    - Статус кеги -> 'full' (если она не была пустой).
    """
    tap = tap_crud.unassign_keg_from_tap(db=db, tap_id=tap_id)
    operator_stream_hub.emit_invalidation(resource="taps", entity_id=str(tap_id), reason="tap_unassign_keg")
    operator_stream_hub.emit_invalidation(resource="today", entity_id=str(tap_id), reason="tap_unassign_keg")
    operator_stream_hub.emit_invalidation(resource="system", entity_id=str(tap_id), reason="tap_unassign_keg")
    return tap


@router.get("/{tap_id}/display-config", response_model=schemas.TapDisplayConfig, summary="Get tap display config")
def read_tap_display_config(tap_id: int, db: Session = Depends(get_db)):
    return display_crud.get_tap_display_config(db=db, tap_id=tap_id)


@router.put("/{tap_id}/display-config", response_model=schemas.TapDisplayConfig, summary="Update tap display config")
def update_tap_display_config(
    tap_id: int,
    tap_display_config: schemas.TapDisplayConfigUpsert,
    _permission_guard: dict = Depends(security.require_permissions("display_override")),
    db: Session = Depends(get_db),
):
    config = display_crud.upsert_tap_display_config(db=db, tap_id=tap_id, payload=tap_display_config)
    operator_stream_hub.emit_invalidation(resource="taps", entity_id=str(tap_id), reason="tap_display_config_updated")
    return schemas.TapDisplayConfig.model_validate(config)
