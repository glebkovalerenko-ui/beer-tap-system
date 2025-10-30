# backend/crud/pour_crud.py
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
import models
import schemas
from crud import card_crud, tap_crud, guest_crud, keg_crud # Импортируем все необходимые CRUD-модули
import uuid

def get_pour_by_client_tx_id(db: Session, client_tx_id: str):
    """Проверяет, существует ли уже транзакция с таким ID от клиента."""
    return db.query(models.Pour).filter(models.Pour.client_tx_id == client_tx_id).first()

def _create_pour_record(db: Session, pour_data: schemas.PourData, guest_id: uuid.UUID, keg_id: uuid.UUID, amount_charged: Decimal, price_per_ml: Decimal):
    """
    (Внутренняя функция) Создает и сохраняет запись о наливе в БД.
    Эта функция является частью более крупной транзакции в process_pour.
    """
    db_pour = models.Pour(
        client_tx_id=pour_data.client_tx_id,
        card_uid=pour_data.card_uid,
        tap_id=pour_data.tap_id,
        volume_ml=pour_data.volume_ml,
        poured_at=pour_data.start_ts, # Используем время начала налива
        amount_charged=amount_charged,
        price_per_ml_at_pour=price_per_ml,
        guest_id=guest_id,
        keg_id=keg_id
    )
    db.add(db_pour)
    return db_pour

def process_pour(db: Session, pour_data: schemas.PourData):
    """
    Основная функция для обработки одного налива.
    Выполняет полную валидацию и атомарное обновление состояния системы.
    """
    # --- ШАГ 1: ВАЛИДАЦИЯ И ОБОГАЩЕНИЕ ДАННЫХ ---
    
    # 1.1. Находим все связанные сущности, "жадно" загружая их связи
    card = db.query(models.Card).options(joinedload(models.Card.guest)).filter(models.Card.card_uid == pour_data.card_uid).first()
    tap = db.query(models.Tap).options(joinedload(models.Tap.keg).joinedload(models.Keg.beverage)).filter(models.Tap.tap_id == pour_data.tap_id).first()

    # 1.2. Проводим бизнес-проверки на существование и статусы
    if not (card and card.guest and tap and tap.keg and tap.keg.beverage):
        return {"status": "rejected", "reason": f"Invalid data: Card UID {pour_data.card_uid} or Tap ID {pour_data.tap_id} not found or not fully configured."}
    
    guest = card.guest
    keg = tap.keg
    beverage = keg.beverage

    if not guest.is_active or card.status != "active":
        return {"status": "rejected", "reason": f"Guest {guest.guest_id} or Card {card.card_uid} is not active."}
    
    if tap.status != "active" or keg.status != "in_use":
        return {"status": "rejected", "reason": f"Tap {tap.tap_id} or Keg {keg.keg_id} is not in 'active'/'in_use' state."}

    # 1.3. Рассчитываем стоимость на сервере и проверяем баланс и остаток
    # Округляем до копеек
    price_per_ml = beverage.sell_price_per_liter / Decimal(1000)
    amount_to_charge = (Decimal(pour_data.volume_ml) * price_per_ml).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if guest.balance < amount_to_charge:
        return {"status": "rejected", "reason": f"Insufficient funds for Guest {guest.guest_id}."}
        
    if keg.current_volume_ml < pour_data.volume_ml:
        # В этом случае мы можем либо отклонить транзакцию, либо списать остаток.
        # Для MVP и простоты - отклоняем.
        return {"status": "rejected", "reason": f"Insufficient volume in Keg {keg.keg_id}."}

    # --- ШАГ 2: АТОМАРНОЕ ОБНОВЛЕНИЕ СОСТОЯНИЯ ---
    try:
        # 2.1. Создаем запись о наливе (Pour)
        _create_pour_record(db, pour_data, guest.guest_id, keg.keg_id, amount_to_charge, price_per_ml)

        # 2.2. Списываем баланс с гостя
        guest.balance -= amount_to_charge

        # 2.3. Уменьшаем остаток в кеге
        keg.current_volume_ml -= pour_data.volume_ml

        # 2.4. Проверяем, не закончилась ли кега
        if keg.current_volume_ml <= 0:
            keg.status = "empty"
            tap.status = "empty"
            keg.finished_at = pour_data.end_ts

        # Коммитить мы не будем здесь. Этим будет управлять вызывающая функция (в main.py),
        # чтобы можно было обработать всю пачку наливов в одной транзакции.
        
        return {"status": "accepted", "reason": "Pour processed successfully."}

    except Exception as e:
        # В случае любой ошибки во время обработки, возвращаем статус rejected
        # Откат транзакции также будет произведен в main.py
        return {"status": "rejected", "reason": f"Internal server error: {str(e)}"}
    
def get_pours(db: Session, skip: int = 0, limit: int = 20):
    """
    Получение списка последних наливов для отображения в UI.
    Жадно подгружает связанные сущности для минимизации запросов к БД.
    """
    return db.query(models.Pour).options(
        joinedload(models.Pour.guest),
        joinedload(models.Pour.tap),
        joinedload(models.Pour.keg).joinedload(models.Keg.beverage)
    ).order_by(models.Pour.poured_at.desc()).offset(skip).limit(limit).all()