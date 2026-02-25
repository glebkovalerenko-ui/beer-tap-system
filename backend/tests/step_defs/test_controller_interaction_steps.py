# backend/tests/step_defs/test_controller_interaction_steps.py

from pytest_bdd import scenarios, when, parsers, given, then
import uuid, models, json
from sqlalchemy.orm import Session
from models import SystemState, Guest, Card, Beverage, Keg, Tap, Pour
from decimal import Decimal
import datetime
from datetime import datetime, date, timezone, timedelta

# Этот файл связывает controller_interaction.feature с нашим тестовым фреймворком.
scenarios('../features/controller_interaction.feature')

# --- When шаги ---

@when(parsers.parse('Контроллер отправляет POST-запрос на /api/controllers/register с уникальным "{field}"'))
def register_new_controller(client, context: dict, field: str):
    """
    Шаг выполнения: отправляет запрос на регистрацию контроллера.
    """
    # Генерируем уникальный ID для каждого запуска теста
    controller_id = f"test-controller-{uuid.uuid4()}"
    payload = {
        "controller_id": controller_id,
        "ip_address": "192.168.1.100",
        "firmware_version": "1.0.0"
    }
    # Сохраняем ID для проверки в БД
    context['controller_id'] = controller_id
    
    print(f"\n[WHEN] Отправка POST-запроса на /api/controllers/register с ID: {controller_id}")
    response = client.post("/api/controllers/register", json=payload)
    context['response'] = response

@given(parsers.parse('Контроллер "{controller_id}" уже существует'))
def create_existing_controller(client, db_session: Session, controller_id: str, context: dict):
    """
    Шаг подготовки: создает в БД контроллер с заданным ID.
    """
    controller_data = {
        "controller_id": controller_id,
        "ip_address": "192.168.1.101", # Старый IP
        "firmware_version": "1.0.0"
    }
    controller = models.Controller(**controller_data)
    db_session.add(controller)
    db_session.commit()
    
    context['controller_id'] = controller_id
    context['new_ip_address'] = "192.168.1.102" # Новый IP для обновления
    print(f"\n[GIVEN] Создан контроллер с ID '{controller_id}' и IP '192.168.1.101'.")

@when(parsers.parse('Контроллер "{controller_id}" отправляет POST-запрос на /api/controllers/register с новым IP'))
def reregister_controller(client, controller_id: str, context: dict):
    """
    Шаг выполнения: отправляет запрос на повторную регистрацию контроллера.
    """
    new_ip = context.get('new_ip_address')
    assert new_ip, "Новый IP-адрес не найден в context."
    
    payload = {
        "controller_id": controller_id,
        "ip_address": new_ip,
        "firmware_version": "1.0.1" # Также обновляем прошивку
    }
    
    print(f"[WHEN] Отправка POST-запроса на /api/controllers/register для '{controller_id}' с новым IP '{new_ip}'.")
    response = client.post("/api/controllers/register", json=payload)
    context['response'] = response

@then(parsers.parse('Запись контроллера "{controller_id}" в БД должна быть обновлена'))
def check_controller_record_is_updated(db_session: Session, controller_id: str, context: dict):
    """
    Шаг проверки: убеждается, что IP-адрес контроллера в БД изменился.
    """
    new_ip = context.get('new_ip_address')
    assert new_ip, "Новый IP-адрес не найден в context для проверки."

    # Находим контроллер в БД по его ID
    db_controller = db_session.query(models.Controller).filter(models.Controller.controller_id == controller_id).one()
    
    print(f"[THEN] Проверка обновления контроллера '{controller_id}'. Ожидаемый IP: {new_ip}, Фактический: {db_controller.ip_address}")
    assert db_controller.ip_address == new_ip, "IP-адрес контроллера в базе данных не был обновлен."
    assert db_controller.firmware_version == "1.0.1", "Версия прошивки не была обновлена."
    print("[THEN] Запись контроллера успешно обновлена.")

@given(parsers.parse('Флаг "{flag_name}" установлен в "{flag_value}"'))
def set_system_state_flag(client, db_session: Session, flag_name: str, flag_value: str):
    """
    Шаг подготовки: устанавливает значение для системного флага в БД (Upsert).
    """
    # Пытаемся найти существующий флаг
    db_flag = db_session.query(SystemState).filter(SystemState.key == flag_name).one_or_none()
    
    if db_flag:
        # Если нашли - обновляем
        db_flag.value = flag_value
        print(f"\n[GIVEN] Обновлен флаг '{flag_name}' на значение '{flag_value}'.")
    else:
        # Если не нашли - создаем
        db_flag = SystemState(key=flag_name, value=flag_value)
        db_session.add(db_flag)
        print(f"\n[GIVEN] Создан флаг '{flag_name}' со значением '{flag_value}'.")
        
    db_session.commit()

@when(parsers.parse("Контроллер отправляет GET-запрос на {url}"))
def get_request_from_controller(client, url: str, context: dict):
    """
    Шаг выполнения: отправляет GET-запрос от имени контроллера (без авторизации).
    """
    print(f"[WHEN] Отправка GET-запроса на {url}")
    response = client.get(url)
    context['response'] = response

@then(parsers.parse('API должен вернуть 200 OK и тело ответа должно содержать "{key}": "{value}"'))
def check_response_body_contains_key_value(context: dict, key: str, value: str):
    """
    Шаг проверки: проверяет, что код ответа 200 и тело ответа
    содержит указанную пару ключ-значение.
    """
    response = context.get('response')
    assert response is not None, "Ответ от API не найден в context."

    # 1. Проверяем код ответа
    assert response.status_code == 200, f"Ожидался код 200, но получен {response.status_code}."
    print(f"[THEN] Код ответа 200 OK подтвержден.")

    # 2. Проверяем наличие ключа и соответствие значения
    actual_body = response.json()
    print(f"[THEN] Проверка наличия '{key}': '{value}' в теле ответа: {actual_body}")
    
    assert key in actual_body, f"Ключ '{key}' не найден в теле ответа."
    # Сравниваем значения как строки, чтобы избежать проблем с типами (e.g. bool vs str)
    assert str(actual_body[key]).lower() == value.lower(), f"Для ключа '{key}' ожидалось значение '{value}', но получено '{actual_body[key]}'."
    print(f"[THEN] Ключ-значение '{key}': '{value}' успешно найдено.")

@given("Гость имеет баланс, кран и кега активны")
def setup_for_valid_pour(client, db_session: Session, context: dict):
    """
    Шаг подготовки: создает полную, готовую к наливу цепочку:
    Гость с балансом -> Карта -> Напиток -> Кега -> Кран -> Кега на кране.
    """
    # 1. Создаем гостя с балансом
    initial_balance = Decimal("1000.00")
    guest = Guest(last_name="Наливайкин", first_name="Валид", phone_number=f"+7999{uuid.uuid4().hex[:7]}",
                  date_of_birth=datetime.date(1990, 1, 1), id_document=f"8888 {uuid.uuid4().hex[:6]}", balance=initial_balance)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)

    # 2. Создаем и привязываем карту
    card_uid = f"VALID-POUR-CARD-{uuid.uuid4().hex[:6]}"
    card = Card(card_uid=card_uid, guest_id=guest.guest_id, status="active")
    db_session.add(card)
    
    # 3. Создаем напиток, кегу, кран и связываем их
    initial_volume_ml = 50000
    beverage = Beverage(name=f"PourBeer-{uuid.uuid4()}", brewery="BDD", style="IPA", abv=7, sell_price_per_liter=Decimal("500.00"))
    keg = Keg(beverage=beverage, initial_volume_ml=initial_volume_ml, current_volume_ml=initial_volume_ml, purchase_price=7000)
    tap = Tap(display_name=f"PourTap-{uuid.uuid4()}")
    db_session.add_all([beverage, keg, tap])
    db_session.commit()
    
    tap.keg_id = keg.keg_id
    keg.status = "in_use"
    tap.status = "active" # Убеждаемся, что и кран тоже активен
    db_session.commit()
    db_session.refresh(guest); db_session.refresh(keg); db_session.refresh(tap)
    
    # 4. Сохраняем все начальные данные в context для проверки
    context['guest_id'] = guest.guest_id
    context['initial_balance'] = initial_balance
    context['card_uid'] = card_uid
    context['tap_id'] = tap.tap_id
    context['keg_id'] = keg.keg_id
    context['initial_volume_ml'] = initial_volume_ml
    context['price_per_liter'] = beverage.sell_price_per_liter
    print(f"\n[GIVEN] Система готова к наливу. Гость: {guest.guest_id}, Баланс: {initial_balance}. Кран: {tap.tap_id}, Кега: {keg.keg_id}.")

@when("Контроллер отправляет POST-запрос на /api/sync/pours/ с валидным наливом")
def send_valid_pour_request(client, context: dict):
    # Рассчитываем стоимость и объем
    pour_volume_ml = 500 # 0.5 литра
    pour_cost_decimal = (context['price_per_liter'] / 1000) * pour_volume_ml
    
    # --- ИСПРАВЛЕНО: Генерируем правильный payload согласно схеме PourData ---
    
    # 1. Генерируем временные метки
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(seconds=5) # Предполагаем, что налив длился 5 секунд
    
    # 2. Формируем payload
    payload_item = {
        "client_tx_id": f"pour-tx-{uuid.uuid4()}",
        "card_uid": context['card_uid'],
        "tap_id": context['tap_id'],
        "short_id": f"S{uuid.uuid4().hex[:6]}",
        "start_ts": start_time.isoformat(), # Отправляем как ISO-строку, FastAPI распарсит
        "end_ts": end_time.isoformat(),
        "volume_ml": pour_volume_ml,
        "price_cents": int(pour_cost_decimal * 100) # Цена в центах/копейках
    }

    # Эндпоинт ожидает список наливов (pours: list[PourData])
    full_payload = {"pours": [payload_item]}
    
    # Сохраняем данные для проверки в БД
    context['pour_volume_ml'] = pour_volume_ml
    context['pour_cost'] = pour_cost_decimal
    
    print(f"[WHEN] Отправка запроса на налив: {full_payload}")
    # Эндпоинт для синхронизации, скорее всего, /api/sync/pours, а не /api/sync/pours/
    response = client.post("/api/sync/pours", json=full_payload)
    context['response'] = response

@then(parsers.parse('API должен вернуть 200 OK со статусом "{status}"'))
def check_pour_response_status(context: dict, status: str):
    """
    Универсальная проверка ответа от эндпоинта /sync/pours.
    Проверяет код 200 и указанный статус ("accepted" или "rejected").
    """
    response = context.get('response')
    assert response is not None, "Ответ от API не найден."
    
    assert response.status_code == 200, f"Ожидался код 200, но получен {response.status_code}."
    print("[THEN] Код ответа 200 OK подтвержден.")
    
    response_json = response.json()
    assert "results" in response_json and len(response_json["results"]) > 0, "Ответ не содержит списка 'results'."
    
    result = response_json["results"][0]
    
    assert result.get("status") == status, f"Ожидался статус '{status}', но получен '{result.get('status')}' с причиной: '{result.get('reason')}'"
    print(f"[THEN] Статус '{status}' в теле ответа подтвержден.")

@then("Баланс гостя и остаток в кеге должны уменьшиться")
def check_balance_and_volume_decreased(db_session: Session, context: dict):
    guest_id = context['guest_id']
    keg_id = context['keg_id']
    
    # Проверяем баланс гостя
    expected_balance = context['initial_balance'] - context['pour_cost']
    db_guest = db_session.query(Guest).get(guest_id)
    print(f"[THEN] Проверка баланса. Ожидаемый: {expected_balance}, Фактический: {db_guest.balance}")
    assert db_guest.balance == expected_balance, "Баланс гостя списан некорректно."
    
    # Проверяем остаток в кеге
    expected_volume = context['initial_volume_ml'] - context['pour_volume_ml']
    db_keg = db_session.query(Keg).get(keg_id)
    print(f"[THEN] Проверка остатка в кеге. Ожидаемый: {expected_volume} мл, Фактический: {db_keg.current_volume_ml} мл")
    assert db_keg.current_volume_ml == expected_volume, "Остаток в кеге списан некорректно."
    print("[THEN] Баланс гостя и остаток в кеге успешно обновлены.")

@given(parsers.parse('Налив с client_tx_id "{tx_id}" уже был обработан'))
def create_processed_pour(client, db_session: Session, tx_id: str, context: dict):
    """
    Шаг подготовки: создает полную цепочку (гость, кега, кран) и "историческую"
    запись о наливе с заданным transaction ID.
    """
    # 1. Создаем всю необходимую инфраструктуру, как в тесте на валидный налив
    initial_balance = Decimal("2000.00")
    initial_volume_ml = 40000
    guest = Guest(last_name="Идемпотентный", first_name="Тест", phone_number=f"+7900{uuid.uuid4().hex[:7]}",
                  date_of_birth=date(1991, 2, 2), id_document=f"7777 {uuid.uuid4().hex[:6]}", balance=initial_balance)
    card = Card(card_uid=f"IDEMPOTENT-CARD-{uuid.uuid4().hex[:6]}", guest=guest, status="active")
    beverage = Beverage(name=f"IdempotentBeer-{uuid.uuid4()}", brewery="BDD", style="Amber Ale", abv=5.5, sell_price_per_liter=Decimal("450.00"))
    keg = Keg(beverage=beverage, initial_volume_ml=50000, current_volume_ml=initial_volume_ml, purchase_price=5500)
    tap = Tap(display_name=f"IdempotentTap-{uuid.uuid4()}")
    db_session.add_all([guest, card, beverage, keg, tap])
    db_session.commit()
    
    tap.keg_id = keg.keg_id
    keg.status = "in_use"
    tap.status = "active"
    db_session.commit()
    
    # 2. Создаем запись о "прошлом" наливе
    pour_record = Pour(
        client_tx_id=tx_id, card_uid=card.card_uid, tap_id=tap.tap_id,
        guest_id=guest.guest_id, keg_id=keg.keg_id,
        volume_ml=100, amount_charged=Decimal("45.00"), poured_at=datetime.now(timezone.utc)
    )
    db_session.add(pour_record)
    db_session.commit()
    db_session.refresh(guest); db_session.refresh(keg)
    
    # 3. Сохраняем все данные в context
    context['duplicate_tx_id'] = tx_id
    context['card_uid'] = card.card_uid
    context['tap_id'] = tap.tap_id
    context['initial_balance'] = guest.balance
    context['initial_volume'] = keg.current_volume_ml
    
    print(f"\n[GIVEN] Создана запись о наливе с tx_id '{tx_id}'. Баланс гостя: {guest.balance}, остаток в кеге: {keg.current_volume_ml}.")

@when("Контроллер повторно отправляет тот же налив")
def resend_duplicate_pour(client, context: dict):
    # Формируем payload, полностью идентичный "прошлому" наливу
    payload_item = {
        "client_tx_id": context['duplicate_tx_id'],
        "card_uid": context['card_uid'],
        "tap_id": context['tap_id'],
        "short_id": f"S{uuid.uuid4().hex[:6]}",
        "start_ts": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "volume_ml": 100,
        "price_cents": 4500
    }
    full_payload = {"pours": [payload_item]}
    
    print(f"[WHEN] Повторная отправка запроса на налив с tx_id: {context['duplicate_tx_id']}")
    response = client.post("/api/sync/pours", json=full_payload)
    context['response'] = response

@then(parsers.parse('API должен вернуть 200 OK со статусом "{status}" и reason "{reason}"'))
def check_pour_response_status_and_reason(context: dict, status: str, reason: str):
    response = context.get('response')
    assert response is not None, "Ответ от API не найден."
    
    assert response.status_code == 200, f"Ожидался код 200, но получен {response.status_code}."
    print("[THEN] Код ответа 200 OK подтвержден.")
    
    response_json = response.json()
    assert "results" in response_json and len(response_json["results"]) > 0, "Ответ не содержит списка 'results'."
    result = response_json["results"][0]
    
    # Для "Insufficient funds" API может добавлять ID гостя в сообщение. Проверяем на вхождение.
    if "Insufficient funds" in reason:
        assert result.get("status") == status, f"Ожидался статус '{status}', но получен '{result.get('status')}'."
        assert reason in result.get("reason", ""), f"В причине ответа не найдена подстрока '{reason}'. Получено: '{result.get('reason')}'"
        print(f"[THEN] Статус '{status}' и причина, содержащая '{reason}', в теле ответа подтверждены.")
    else:
        assert result.get("status") == status, f"Ожидался статус '{status}', но получен '{result.get('status')}'."
        assert result.get("reason") == reason, f"Ожидалась причина '{reason}', но получена '{result.get('reason')}'."
        print(f"[THEN] Статус '{status}' и причина '{reason}' в теле ответа подтверждены.")

@then("Баланс и остаток НЕ должны измениться")
def check_balance_and_volume_unchanged(db_session: Session, context: dict):
    # Находим гостя и кегу по ID, сохраненным в context
    guest = db_session.query(Guest).filter(Guest.cards.any(card_uid=context['card_uid'])).one()
    keg = db_session.query(Keg).join(Tap).filter(Tap.tap_id == context['tap_id']).one()
    
    initial_balance = context['initial_balance']
    initial_volume = context['initial_volume']
    
    print(f"[THEN] Проверка баланса. Начальный: {initial_balance}, Текущий: {guest.balance}")
    assert guest.balance == initial_balance, "Баланс гостя изменился, хотя не должен был."
    
    print(f"[THEN] Проверка остатка в кеге. Начальный: {initial_volume} мл, Текущий: {keg.current_volume_ml} мл")
    assert keg.current_volume_ml == initial_volume, "Остаток в кеге изменился, хотя не должен был."
    print("[THEN] Баланс гостя и остаток в кеге не изменились, как и ожидалось.")

@given("Стоимость налива превышает баланс гостя")
def setup_for_insufficient_funds(client, db_session: Session, context: dict):
    """
    Шаг подготовки: создает гостя с заведомо недостаточным балансом.
    """
    # Создаем полную инфраструктуру
    initial_balance = Decimal("10.00") # Очень маленький баланс
    guest = Guest(last_name="Бедняков", first_name="Тест", phone_number=f"+7922{uuid.uuid4().hex[:7]}",
                  date_of_birth=date(1995, 5, 5), id_document=f"6666 {uuid.uuid4().hex[:6]}", balance=initial_balance)
    card = Card(card_uid=f"NO-FUNDS-CARD-{uuid.uuid4().hex[:6]}", guest=guest, status="active")
    # Напиток с высокой ценой
    beverage = Beverage(name=f"ExpensiveBeer-{uuid.uuid4()}", brewery="BDD", style="Barleywine", abv=12.0, sell_price_per_liter=Decimal("2000.00"))
    keg = Keg(beverage=beverage, initial_volume_ml=50000, current_volume_ml=50000, purchase_price=15000)
    tap = Tap(display_name=f"ExpensiveTap-{uuid.uuid4()}")
    db_session.add_all([guest, card, beverage, keg, tap])
    db_session.commit()
    
    tap.keg_id = keg.keg_id
    keg.status = "in_use"
    tap.status = "active"
    db_session.commit()
    
    # Сохраняем данные для context
    context['card_uid'] = card.card_uid
    context['tap_id'] = tap.tap_id
    
    print(f"\n[GIVEN] Создан гость с балансом {initial_balance} и дорогой напиток на кране.")

@when("Контроллер отправляет этот налив")
def send_pour_with_insufficient_funds(client, context: dict):
    # Формируем payload для налива, который будет стоить дороже, чем баланс гостя (200 мл * 2р/мл = 400р)
    payload_item = {
        "client_tx_id": f"no-funds-tx-{uuid.uuid4()}",
        "card_uid": context['card_uid'],
        "tap_id": context['tap_id'],
        "short_id": f"S{uuid.uuid4().hex[:6]}",
        "start_ts": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=2)).isoformat(),
        "end_ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "volume_ml": 200,
        "price_cents": 40000 # 400 рублей
    }
    full_payload = {"pours": [payload_item]}
    
    print(f"[WHEN] Отправка запроса на налив, который гость не может себе позволить.")
    response = client.post("/api/sync/pours", json=full_payload)
    context['response'] = response

@given('Кран имеет статус "locked"')
def given_tap_is_locked(db_session: Session, context: dict):
    """
    Шаг подготовки: создает полную инфраструктуру (гость, карта, напиток, кега),
    но оставляет кран в статусе 'locked' (не привязанным к кеге).
    """
    # 1. Создаем все необходимые сущности
    guest = Guest(last_name="Блокировкин", first_name="Тест", phone_number=f"+7933{uuid.uuid4().hex[:7]}",
              date_of_birth=date(1993, 3, 3), id_document=f"5555 {uuid.uuid4().hex[:6]}", balance=Decimal("500.00"))
    card = Card(card_uid=f"LOCKED-TAP-CARD-{uuid.uuid4().hex[:6]}", guest=guest, status="active")
    beverage = Beverage(name=f"LockedBeer-{uuid.uuid4()}", brewery="BDD", style="Stout", abv=8.0, sell_price_per_liter=Decimal("600.00"))
    keg = Keg(beverage=beverage, initial_volume_ml=50000, current_volume_ml=50000, purchase_price=Decimal("7000"))
    # 2. Создаем кран, но НЕ привязываем к нему кегу. Его статус по умолчанию 'locked'.
    tap = Tap(display_name=f"LockedTap-{uuid.uuid4()}")
    db_session.add_all([guest, card, beverage, keg, tap])
    db_session.commit()
    
    # 3. Сохраняем данные для шага 'Когда'
    context['card_uid'] = card.card_uid
    context['tap_id'] = tap.tap_id
    
    print(f"\n[GIVEN] Создан гость, карта и кран {tap.tap_id} со статусом 'locked'.")


@when("Контроллер отправляет налив с этого крана")
def when_controller_sends_pour_from_this_tap(client, context: dict):
    """
    Шаг выполнения: отправляет запрос на налив, используя ID заблокированного крана.
    """
    payload_item = {
        "client_tx_id": f"locked-tap-tx-{uuid.uuid4()}",
        "card_uid": context['card_uid'],
        "tap_id": context['tap_id'],
        "short_id": f"S{uuid.uuid4().hex[:6]}",
        "start_ts": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "volume_ml": 100,
        "price_cents": 6000 # 60 рублей
    }
    full_payload = {"pours": [payload_item]}
    
    print(f"[WHEN] Отправка запроса на налив с заблокированного крана {context['tap_id']}.")
    response = client.post("/api/sync/pours", json=full_payload)
    context['response'] = response

@given("Остаток в кеге равен объему налива")
def given_keg_volume_equals_pour_volume(db_session: Session, context: dict):
    """
    Шаг подготовки: создает инфраструктуру, где в кеге осталось ровно столько напитка,
    сколько будет в запросе на налив.
    """
    pour_volume = 500  # Объем, который опустошит кегу (в мл)
    
    # 1. Создаем гостя, карту, напиток, кегу и кран.
    guest = Guest(last_name="Последнекаплев", first_name="Тест", phone_number=f"+7944{uuid.uuid4().hex[:7]}",
                  date_of_birth=date(1994, 4, 4), id_document=f"4444 {uuid.uuid4().hex[:6]}", balance=Decimal("1000.00"))
    card = Card(card_uid=f"EMPTYING-POUR-CARD-{uuid.uuid4().hex[:6]}", guest=guest, status="active")
    beverage = Beverage(name=f"EmptyingBeer-{uuid.uuid4()}", brewery="BDD", style="Porter", abv=6.0, sell_price_per_liter=Decimal("500.00"))
    # 2. Создаем кегу, где current_volume_ml РАВЕН объему будущего налива.
    keg = Keg(beverage=beverage, initial_volume_ml=50000, current_volume_ml=pour_volume, purchase_price=Decimal("6000"), status="in_use")
    tap = Tap(display_name=f"EmptyingTap-{uuid.uuid4()}", keg=keg, status="active")
    db_session.add_all([guest, card, beverage, keg, tap])
    db_session.commit()
    
    # 3. Сохраняем данные для следующих шагов
    context['card_uid'] = card.card_uid
    context['tap_id'] = tap.tap_id
    context['keg_id'] = keg.keg_id
    context['pour_volume_ml'] = pour_volume
    context['price_per_liter'] = beverage.sell_price_per_liter
    
    print(f"\n[GIVEN] В кеге {keg.keg_id} осталось {pour_volume} мл. Подготовлен налив на тот же объем.")

@when("Контроллер отправляет этот налив")
def when_controller_sends_insufficient_funds_pour(client, context: dict):
    """
    Шаг выполнения для сценария с недостаточным балансом.
    Формирует payload для налива, который гость не может себе позволить.
    """
    payload_item = {
        "client_tx_id": f"no-funds-tx-{uuid.uuid4()}",
        "card_uid": context['card_uid'],
        "tap_id": context['tap_id'],
        "short_id": f"S{uuid.uuid4().hex[:6]}",
        "start_ts": (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "volume_ml": 200,
        "price_cents": 40000 # 400 рублей
    }
    full_payload = {"pours": [payload_item]}
    
    print(f"[WHEN] Отправка запроса на налив, который гость не может себе позволить.")
    response = client.post("/api/sync/pours", json=full_payload)
    context['response'] = response

@then('Статус кеги и крана должен измениться на "empty"')
def then_keg_and_tap_status_should_be_empty(db_session: Session, context: dict):
    """
    Шаг проверки: убеждается, что и кега, и кран получили статус 'empty'.
    """
    keg_id = context['keg_id']
    tap_id = context['tap_id']
    
    db_keg = db_session.query(Keg).get(keg_id)
    db_tap = db_session.query(Tap).get(tap_id)
    
    print(f"[THEN] Проверка статусов. Кега: {db_keg.status}, Кран: {db_tap.status}")
    
    assert db_keg.status == "empty", f"Ожидался статус 'empty' для кеги, но получен '{db_keg.status}'."
    assert db_tap.status == "empty", f"Ожидался статус 'empty' для крана, но получен '{db_tap.status}'."
    
    print("[THEN] Статусы кеги и крана корректно изменены на 'empty'.")
