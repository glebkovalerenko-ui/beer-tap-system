# backend/crud/controller_crud.py
from sqlalchemy.orm import Session
import models
import schemas

def get_controllers(db: Session):
    """Возвращает список всех зарегистрированных контроллеров."""
    return db.query(models.Controller).all()

def register_controller(db: Session, controller: schemas.ControllerRegister) -> models.Controller:
    """
    Регистрирует или обновляет информацию о контроллере.
    Это реализация логики "upsert".
    """
    # 1. Пытаемся найти существующий контроллер по ID
    db_controller = db.query(models.Controller).filter(models.Controller.controller_id == controller.controller_id).first()

    if db_controller:
        # 2. Если контроллер найден - обновляем его данные
        db_controller.ip_address = controller.ip_address
        db_controller.firmware_version = controller.firmware_version
        # Поле `last_seen` обновится автоматически благодаря `onupdate` в модели
    else:
        # 3. Если контроллер не найден - создаем новую запись
        db_controller = models.Controller(**controller.dict())
        db.add(db_controller)
    
    # 4. Сохраняем изменения в БД
    db.commit()
    db.refresh(db_controller)
    return db_controller