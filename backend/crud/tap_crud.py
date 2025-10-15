import uuid
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
import models, schemas
from crud import keg_crud

def get_tap(db: Session, tap_id: int):
    """
    Получение одного крана по ID.
    Сразу же подгружает связанную кегу и информацию о напитке в ней.
    """
    db_tap = db.query(models.Tap).options(
        # --- ПРИМЕНЯЕМ ЦЕПОЧКУ ЖАДНОЙ ЗАГРУЗКИ ---
        joinedload(models.Tap.keg).joinedload(models.Keg.beverage)
    ).filter(models.Tap.tap_id == tap_id).first()
    
    if db_tap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tap not found")
    return db_tap

def get_tap_by_display_name(db: Session, name: str):
    """ Получение крана по его отображаемому имени. """
    return db.query(models.Tap).filter(models.Tap.display_name == name).first()

def get_taps(db: Session, skip: int = 0, limit: int = 100):
    """
    Получение списка всех кранов.
    Сразу же подгружает связанные кеги и информацию о напитках.
    """
    return db.query(models.Tap).options(
        joinedload(models.Tap.keg).joinedload(models.Keg.beverage)
    ).offset(skip).limit(limit).all()

def create_tap(db: Session, tap: schemas.TapCreate):
    """ Создание нового крана. """
    if get_tap_by_display_name(db, name=tap.display_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tap with this display name already exists")
    
    # Статус по умолчанию ('locked') будет установлен самой моделью
    db_tap = models.Tap(display_name=tap.display_name)
    
    db.add(db_tap)
    db.commit()
    db.refresh(db_tap)
    return db_tap

def update_tap(db: Session, tap_id: int, tap_update: schemas.TapUpdate):
    """ Обновление данных крана (имя или статус). """
    db_tap = get_tap(db, tap_id=tap_id)
    
    update_data = tap_update.model_dump(exclude_unset=True)

    # Проверяем уникальность нового имени, если оно было передано
    if 'display_name' in update_data and update_data['display_name'] != db_tap.display_name:
        if get_tap_by_display_name(db, name=update_data['display_name']):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tap with this display name already exists")

    for key, value in update_data.items():
        setattr(db_tap, key, value)
        
    db.commit()
    db.refresh(db_tap)
    return db_tap
    
def delete_tap(db: Session, tap_id: int):
    """ Удаление крана. """
    db_tap = get_tap(db, tap_id=tap_id)

    # --- БИЗНЕС-ПРАВИЛО: Нельзя удалить кран, к которому подключена кега ---
    if db_tap.keg_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a tap with a keg attached. Please unassign the keg first."
        )
        
    db.delete(db_tap)
    db.commit()
    return db_tap

def assign_keg_to_tap(db: Session, tap_id: int, keg_id: uuid.UUID):
    """
    Назначает кегу на кран, выполняя все необходимые бизнес-проверки.
    Является идемпотентной.
    """
    db_tap = get_tap(db, tap_id=tap_id)
    
    # --- ПРОВЕРКА ИДЕМПОТЕНТНОСТИ ---
    if db_tap.keg_id == keg_id:
        return db_tap # Кега уже назначена, ничего не делаем, возвращаем успех

    # --- БИЗНЕС-ПРАВИЛА ---
    if db_tap.keg_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tap {tap_id} is already occupied by keg {db_tap.keg_id}")
    
    db_keg = keg_crud.get_keg(db, keg_id=keg_id)
    if db_keg.status != 'full':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Keg {keg_id} is not full. Current status: {db_keg.status}")

    # --- ИЗМЕНЕНИЕ СОСТОЯНИЙ (АТОМАРНАЯ ОПЕРАЦИЯ) ---
    db_tap.keg_id = keg_id
    db_tap.status = 'active'
    
    # Обновляем кегу через keg_crud для соблюдения логики
    keg_update_schema = schemas.KegUpdate(status='in_use')
    keg_crud.update_keg(db=db, keg_id=keg_id, keg_update=keg_update_schema)
    
    db.commit()
    db.refresh(db_tap)
    
    return db_tap

def unassign_keg_from_tap(db: Session, tap_id: int):
    """ Снимает кегу с крана. """
    db_tap = get_tap(db, tap_id=tap_id)
    
    if db_tap.keg_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tap {tap_id} has no keg assigned.")
    
    keg_id = db_tap.keg_id
    db_keg = keg_crud.get_keg(db, keg_id=keg_id)

    # --- ИЗМЕНЕНИЕ СОСТОЯНИЙ ---
    db_tap.keg_id = None
    db_tap.status = 'locked' # Возвращаем в безопасное состояние

    # Меняем статус кеги, только если она не пустая. Пустая остается пустой.
    if db_keg.status == 'in_use':
         keg_update_schema = schemas.KegUpdate(status='full') # Считаем ее снова доступной
         keg_crud.update_keg(db=db, keg_id=keg_id, keg_update=keg_update_schema)

    db.commit()
    db.refresh(db_tap)
    return db_tap