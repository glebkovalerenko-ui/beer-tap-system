# backend/crud/pour_crud.py
from sqlalchemy.orm import Session
from decimal import Decimal
import models, schemas
# Импортируем наши CRUD-модули
from . import card_crud, tap_crud, guest_crud # Убедимся, что guest_crud импортирован

def get_pour_by_client_tx_id(db: Session, client_tx_id: str):
    """
    Проверяет, существует ли уже транзакция с таким ID от клиента.
    """
    return db.query(models.Pour).filter(models.Pour.client_tx_id == client_tx_id).first()

def create_pour(db: Session, pour: schemas.PourData):
    """
    Создает новую запись о наливе, выполняя всю необходимую бизнес-логику,
    включая списание баланса.
    """
    # --- ШАГ 1: НАХОДИМ СВЯЗАННЫЕ СУЩНОСТИ ---
    
    card = card_crud.get_card_by_uid(db, card_uid=pour.card_uid)
    if not card:
        raise ValueError(f"Карта с UID {pour.card_uid} не найдена!")
    
    tap = tap_crud.get_tap_by_id(db, tap_id=pour.tap_id)
    if not tap:
        raise ValueError(f"Кран с ID {pour.tap_id} не найден!")

    # --- НОВЫЙ ШАГ 1.1: НАХОДИМ ГОСТЯ И ПРОВЕРЯЕМ БАЛАНС ---
    # Используем существующую функцию из guest_crud.py
    guest = guest_crud.get_guest(db, guest_id=card.guest_id)
    if not guest:
        # Эта ошибка вряд ли произойдет, если работает внешний ключ, но проверка важна
        raise ValueError(f"Связанный гость с ID {card.guest_id} не найден!")
        
    amount_to_charge = Decimal(pour.price_cents) / 100

    # Проверка баланса. Для MVP мы не будем блокировать налив,
    # но в будущем эта проверка станет критически важной.
    if guest.balance < amount_to_charge:
        # Пока просто выведем предупреждение в лог сервера
        print(f"ВНИМАНИЕ: У гостя {guest.guest_id} недостаточно средств. Баланс уйдет в минус.")
    
    # --- ШАГ 2: АДАПТАЦИЯ ДАННЫХ ---
    price_per_ml = amount_to_charge / Decimal(pour.volume_ml) if pour.volume_ml > 0 else 0
    
    # --- ШАГ 3: СОЗДАЕМ ОБЪЕКТ POUR ---
    db_pour = models.Pour(
        client_tx_id=pour.client_tx_id,
        card_uid=pour.card_uid,
        tap_id=pour.tap_id,
        volume_ml=pour.volume_ml,
        poured_at=pour.start_ts,
        amount_charged=amount_to_charge,
        price_per_ml_at_pour=price_per_ml,
        guest_id=card.guest_id,
        keg_id=tap.keg_id
    )

    # --- НОВЫЙ ШАГ 4: СПИСЫВАЕМ БАЛАНС ---
    guest.balance = guest.balance - amount_to_charge
    
    # Добавляем оба измененных объекта в сессию.
    # SQLAlchemy сама разберется, что один нужно создать (INSERT), а второй обновить (UPDATE).
    db.add(db_pour)
    db.add(guest)
    
    return db_pour