# backend/api/taps.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import schemas, security
from crud import tap_crud
from database import get_db

router = APIRouter(
    prefix="/taps",
    tags=["Taps"],
    dependencies=[Depends(security.get_current_user)]
)

@router.post("/", response_model=schemas.Tap, status_code=status.HTTP_201_CREATED, summary="Добавить новый кран")
def create_tap(tap: schemas.TapCreate, db: Session = Depends(get_db)):
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
def update_tap(tap_id: int, tap_update: schemas.TapUpdate, db: Session = Depends(get_db)):
    """
    Обновляет информацию о кране (например, его отображаемое имя или статус).
    """
    return tap_crud.update_tap(db=db, tap_id=tap_id, tap_update=tap_update)

@router.delete("/{tap_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить кран")
def delete_tap(tap_id: int, db: Session = Depends(get_db)):
    """
    Удаляет кран из системы.

    **Бизнес-правило:** Запрещено удалять кран, к которому в данный момент
    подключена кега.
    """
    tap_crud.delete_tap(db=db, tap_id=tap_id)
    return # Возвращаем 204 No Content

@router.put("/{tap_id}/keg", response_model=schemas.Tap, summary="Назначить кегу на кран")
def assign_keg(tap_id: int, assignment: schemas.TapAssignKeg, db: Session = Depends(get_db)):
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
    return tap_crud.assign_keg_to_tap(db=db, tap_id=tap_id, keg_id=assignment.keg_id)

@router.delete("/{tap_id}/keg", response_model=schemas.Tap, summary="Снять кегу с крана")
def unassign_keg(tap_id: int, db: Session = Depends(get_db)):
    """
    Снимает текущую кегу с крана.

    **Побочные эффекты:**
    - Статус крана -> 'locked'.
    - Статус кеги -> 'full' (если она не была пустой).
    """
    return tap_crud.unassign_keg_from_tap(db=db, tap_id=tap_id)