# backend/tests/step_defs/test_guest_finance_steps.py

from pytest_bdd import scenarios, then, parsers, given, when
from models import Guest, Card, Transaction, Beverage, Keg, Tap
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
import models, uuid, pytest

# Указываем, какой feature-файл реализуют шаги из этого файла
scenarios('../features/guest_finance.feature')

# --- СПЕЦИФИЧНЫЕ Then шаги ---

@given(parsers.parse('Существует гость с {field} "{value}"'))
def create_existing_guest_by_field(client, db_session: Session, field: str, value: str, context: dict):
    """
    Шаг подготовки: создает в БД гостя с указанным уникальным полем (телефоном или документом).
    """
    guest_data = {
        "last_name": "Дубликатов",
        "first_name": "Иван",
        "phone_number": "+70000000000",
        "date_of_birth": date(2000, 1, 1),
        "id_document": "0000 000000"
    }
    
    # Определяем, какое поле нужно установить в переданное значение
    if field == "телефоном":
        field_name = "phone_number"
        context['duplicate_field'] = 'phone_number'
    elif field == "документом":
        field_name = "id_document"
        context['duplicate_field'] = 'id_document'
    else:
        pytest.fail(f"Неизвестное поле для создания гостя: {field}")

    guest_data[field_name] = value
    context['duplicate_value'] = value

    existing_guest = Guest(**guest_data)
    db_session.add(existing_guest)
    db_session.commit()
    print(f"\n[GIVEN] Создан гость с {field} '{value}' для теста на дублирование.")

@when(parsers.parse("Клиент пытается создать нового гостя с тем же {field}"))
def attempt_to_create_duplicate_guest_by_field(client, context: dict, field: str):
    """
    Шаг выполнения: пытается создать второго гостя с тем же уникальным полем.
    """
    access_token = context.get("access_token")
    assert access_token is not None, "Токен доступа не найден."
    
    duplicate_field = context.get('duplicate_field')
    duplicate_value = context.get('duplicate_value')
    assert duplicate_field and duplicate_value, "Данные для дублирования не найдены в context."

    payload = {
        "last_name": "Новый", "first_name": "Петр",
        "phone_number": "+79998887766", "date_of_birth": "1999-12-31",
        "id_document": "9999 888777"
    }
    # Устанавливаем дублирующееся значение в нужное поле
    payload[duplicate_field] = duplicate_value
    
    print(f"[WHEN] Попытка создать гостя с уже существующим полем '{duplicate_field}':'{duplicate_value}'.")
    response = client.post("/api/guests/", headers={"Authorization": f"Bearer {access_token}"}, json=payload)
    context['response'] = response

@given(parsers.parse('Существует гость с фамилией "{last_name}"'))
def create_guest_with_last_name(client, db_session: Session, last_name: str, context: dict):
    """
    Шаг подготовки: создает в БД гостя с указанной фамилией и сохраняет его ID.
    """
    guest_data = {
        "last_name": last_name,
        "first_name": "Петр",
        "phone_number": "+79334445566",
        "date_of_birth": date(1980, 5, 25),
        "id_document": "3333 444555"
    }
    new_guest = Guest(**guest_data)
    db_session.add(new_guest)
    db_session.commit()
    db_session.refresh(new_guest) # Обновляем объект, чтобы получить guest_id из БД

    # Сохраняем ID созданного гостя и новый телефон для следующих шагов
    context['guest_id'] = new_guest.guest_id
    context['new_phone_number'] = "+79556667788"
    
    print(f"\n[GIVEN] Создан гость '{last_name}' с ID: {new_guest.guest_id}")

@when(parsers.parse("Клиент отправляет PUT-запрос на /api/guests/{guest_id} с новым номером телефона"))
def update_guest_phone_number(client, context: dict):
    """
    Шаг выполнения: обновляет номер телефона для гостя, созданного на шаге Given.
    """
    access_token = context.get("access_token")
    guest_id = context.get("guest_id")
    new_phone = context.get("new_phone_number")
    assert access_token and guest_id and new_phone, "Необходимые данные (токен, ID гостя, новый телефон) не найдены в context."

    url = f"/api/guests/{guest_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"phone_number": new_phone}
    
    print(f"[WHEN] Отправка PUT-запроса на {url} с данными {payload}")
    response = client.put(url, headers=headers, json=payload)
    context['response'] = response

@then("Запись гостя в БД должна быть обновлена")
def check_guest_record_is_updated(db_session: Session, context: dict):
    """
    Шаг проверки: убеждается, что номер телефона в записи гостя был изменен.
    """
    guest_id = context.get("guest_id")
    new_phone = context.get("new_phone_number")
    assert guest_id and new_phone, "ID гостя или новый телефон не найдены в context для проверки."

    # Находим гостя в БД по его ID
    updated_guest = db_session.query(Guest).filter(Guest.guest_id == guest_id).one()
    
    print(f"[THEN] Проверка обновления в БД. Ожидаемый телефон: {new_phone}, Фактический: {updated_guest.phone_number}")
    assert updated_guest.phone_number == new_phone, "Номер телефона в базе данных не был обновлен."
    print("[THEN] Запись в БД успешно обновлена.")

@given(parsers.parse('Существует гость "{last_name}"'))
def create_guest_for_card_test(client, db_session: Session, last_name: str, context: dict):
    """
    Шаг подготовки: создает гостя и сохраняет его ID для теста с картами.
    """
    guest_data = {
        "last_name": last_name, "first_name": "Сергей",
        "phone_number": f"+79778889900", "date_of_birth": date(1992, 10, 10),
        "id_document": "7777 888999"
    }
    guest = Guest(**guest_data)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)
    
    context['guest_id'] = guest.guest_id
    context['new_card_uid'] = "NEW-CARD-UID-123" # Задаем UID новой карты
    print(f"\n[GIVEN] Создан гость '{last_name}' с ID: {guest.guest_id}")

@when(parsers.parse('Клиент отправляет POST-запрос на /api/guests/{guest_id}/cards с новым "card_uid"'))
def assign_new_card_to_guest(client, context: dict):
    """
    Шаг выполнения: отправляет запрос на привязку новой карты к гостю.
    """
    access_token = context.get("access_token")
    guest_id = context.get("guest_id")
    card_uid = context.get("new_card_uid")
    assert all([access_token, guest_id, card_uid]), "Необходимые данные не найдены в context."

    url = f"/api/guests/{guest_id}/cards"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"card_uid": card_uid}
    
    print(f"[WHEN] Отправка POST-запроса на {url} с данными {payload}")
    response = client.post(url, headers=headers, json=payload)
    context['response'] = response

@then(parsers.parse('В таблице "cards" должна появиться новая запись со статусом "{status}"'))
def check_card_table_for_new_record(db_session: Session, status: str, context: dict):
    """
    Шаг проверки: находит в БД карту по UID и проверяет ее статус и принадлежность гостю.
    """
    guest_id = context.get("guest_id")
    card_uid = context.get("new_card_uid")
    assert guest_id and card_uid, "Данные для проверки карты не найдены в context."

    # Находим карту в БД по ее уникальному UID
    db_card = db_session.query(Card).filter(Card.card_uid == card_uid).one_or_none()

    assert db_card is not None, f"Карта с UID '{card_uid}' не найдена в базе данных."
    print(f"[THEN] Проверка карты '{card_uid}'. Ожидаемый статус: '{status}', фактический: '{db_card.status}'.")
    assert db_card.status == status, "Статус карты в БД не соответствует ожидаемому."
    assert db_card.guest_id == guest_id, "Карта не была привязана к правильному гостю."
    print(f"[THEN] Карта успешно найдена, статус '{status}' и привязка к гостю корректны.")

@given(parsers.parse('Карта "{card_uid}" привязана к гостю'))
def create_guest_with_active_card(client, db_session: Session, card_uid: str, context: dict):
    """
    Шаг подготовки: создает гостя, создает карту и привязывает ее к гостю.
    """
    # 1. Создаем гостя
    guest_data = {
        "last_name": "Карточкин", "first_name": "Афанасий",
        "phone_number": "+79887776655", "date_of_birth": date(1975, 3, 15),
        "id_document": "8888 999000"
    }
    guest = Guest(**guest_data)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)
    
    # 2. Создаем и привязываем карту
    card_data = {
        "card_uid": card_uid,
        "guest_id": guest.guest_id,
        "status": "active" # Изначально карта активна
    }
    card = Card(**card_data)
    db_session.add(card)
    db_session.commit()
    
    # 3. Сохраняем данные в context
    context['guest_id'] = guest.guest_id
    context['card_uid'] = card_uid
    
    print(f"\n[GIVEN] Создан гость {guest.guest_id} с привязанной картой {card_uid} (статус: active).")

@when(parsers.parse("Клиент отправляет DELETE-запрос на /api/guests/{guest_id}/cards/{card_uid}"))
def unassign_card_from_guest(client, context: dict):
    """
    Шаг выполнения: отправляет запрос на отвязывание карты от гостя.
    """
    access_token = context.get("access_token")
    guest_id = context.get("guest_id")
    card_uid = context.get("card_uid")
    assert all([access_token, guest_id, card_uid]), "Необходимые данные не найдены в context."

    url = f"/api/guests/{guest_id}/cards/{card_uid}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print(f"[WHEN] Отправка DELETE-запроса на {url}")
    response = client.delete(url, headers=headers)
    context['response'] = response

@then(parsers.parse('Статус карты "{card_uid}" в БД должен стать "{expected_status}"'))
def check_card_status_in_db(db_session: Session, card_uid: str, expected_status: str):
    """
    Шаг проверки: находит карту по UID и проверяет, что ее статус изменился на ожидаемый.
    """
    # Находим карту в БД по ее уникальному UID
    db_card = db_session.query(Card).filter(Card.card_uid == card_uid).one()

    print(f"[THEN] Проверка статуса карты '{card_uid}'. Ожидаемый: '{expected_status}', Фактический: '{db_card.status}'.")
    assert db_card.status == expected_status, "Статус карты в базе данных не был обновлен."
    # Дополнительная проверка, что карта теперь не привязана к гостю
    assert db_card.guest_id is None, "Поле guest_id не было очищено после отвязки карты."
    print(f"[THEN] Статус карты успешно изменен на '{expected_status}' и карта отвязана от гостя.")

@given(parsers.parse('Гость "{last_name}" имеет баланс "{initial_balance}"'))
def create_guest_with_balance(client, db_session: Session, last_name: str, initial_balance: str, context: dict):
    """
    Шаг подготовки: создает гостя с заданным начальным балансом.
    """
    guest_data = {
        "last_name": last_name, "first_name": "Кирилл",
        "phone_number": "+79123456789", "date_of_birth": date(1988, 11, 1),
        "id_document": "1111 222333",
        "balance": Decimal(initial_balance) # Используем Decimal для точности
    }
    guest = Guest(**guest_data)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)
    
    context['guest_id'] = guest.guest_id
    print(f"\n[GIVEN] Создан гость '{last_name}' с ID {guest.guest_id} и балансом {initial_balance}.")

@when(parsers.parse("Клиент отправляет POST-запрос на /api/guests/{guest_id}/topup с суммой {amount:f}"))
def topup_guest_balance(client, context: dict, amount: float):
    """
    Шаг выполнения: отправляет запрос на пополнение баланса.
    {amount:f} - парсер для чисел с плавающей точкой.
    """
    access_token = context.get("access_token")
    guest_id = context.get("guest_id")
    assert access_token and guest_id, "Необходимые данные не найдены в context."

    url = f"/api/guests/{guest_id}/topup"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"amount": amount, "payment_method": "cash"} # Добавляем метод оплаты

    shift_open = client.post("/api/shifts/open", headers=headers)
    assert shift_open.status_code in (200, 409)
    
    print(f"[WHEN] Отправка POST-запроса на {url} с суммой {amount}")
    response = client.post(url, headers=headers, json=payload)
    context['response'] = response

@then(parsers.parse('Баланс гостя в БД должен стать "{expected_balance}"'))
def check_guest_balance(db_session: Session, expected_balance: str, context: dict):
    """
    Шаг проверки: убеждается, что баланс гостя в БД равен ожидаемому.
    """
    guest_id = context.get("guest_id")
    assert guest_id, "ID гостя не найден в context для проверки."

    # Находим гостя в БД по его ID
    guest = db_session.query(Guest).filter(Guest.guest_id == guest_id).one()
    
    expected_decimal = Decimal(expected_balance)
    print(f"[THEN] Проверка баланса. Ожидаемый: {expected_decimal}, Фактический: {guest.balance}")
    assert guest.balance == expected_decimal, "Баланс гостя в БД не соответствует ожидаемому."
    print("[THEN] Баланс гостя успешно обновлен.")

@when(parsers.parse('Клиент отправляет POST-запрос на /api/guests/ без поля "{missing_field}"'))
def attempt_create_guest_with_missing_field(client, context: dict, missing_field: str):
    """
    Отправляет запрос на создание гостя с JSON-телом,
    в котором умышленно отсутствует одно из обязательных полей.
    """
    access_token = context.get("access_token")
    assert access_token, "Токен доступа не найден в context. Шаг 'Дано Администратор авторизован' должен быть выполнен перед этим шагом."
    headers = {"Authorization": f"Bearer {access_token}"}

    # Лучшая практика для негативных тестов:
    # 1. Начать с полностью валидного payload.
    payload = {
        "last_name": "Валидный",
        "first_name": "Тест",
        "patronymic": "Сергеевич",
        "phone_number": "+79010203045",
        "date_of_birth": "2001-01-10",
        "id_document": "5555 666777"
    }

    # 2. Целенаправленно удалить из него только одно поле, указанное в Gherkin-шаге.
    #    Это гарантирует, что тест проверяет именно отсутствие поля, а не что-то еще.
    if missing_field in payload:
        del payload[missing_field]
    else:
        pytest.fail(f"Поле '{missing_field}', указанное для удаления в .feature файле, не найдено в эталонном payload в коде шага.")

    print(f"\n[WHEN] Отправка запроса на создание гостя без обязательного поля '{missing_field}'. Payload: {payload}")
    response = client.post("/api/guests/", headers=headers, json=payload)
    context["response"] = response

@given(parsers.parse('Карта "{card_uid}" привязана к другому гостю'))
def given_a_card_is_assigned_to_another_guest(db_session: Session, card_uid: str, context: dict):
    """
    Шаг подготовки: создает двух гостей. Первому гостю ("другому")
    привязывает карту с указанным UID. Второго гостя ("нового")
    оставляет без карты, сохраняя его ID для следующего шага.
    """
    # 1. Создаем "другого" гостя, который будет владеть картой.
    owner_guest = Guest(
        last_name="Владельцев", first_name="Кармен", phone_number=f"+7944{uuid.uuid4().hex[:7]}",
        date_of_birth=date(1985, 4, 1), id_document=f"4444 {uuid.uuid4().hex[:6]}"
    )
    db_session.add(owner_guest)
    db_session.commit()
    db_session.refresh(owner_guest)

    # 2. Создаем карту и привязываем ее к первому гостю.
    taken_card = Card(card_uid=card_uid, guest_id=owner_guest.guest_id, status="active")
    db_session.add(taken_card)

    # 3. Создаем "нового" гостя, к которому мы будем пытаться привязать занятую карту.
    new_guest = Guest(
        last_name="Претендентов", first_name="Петр", phone_number=f"+7955{uuid.uuid4().hex[:7]}",
        date_of_birth=date(1995, 5, 2), id_document=f"5555 {uuid.uuid4().hex[:6]}"
    )
    db_session.add(new_guest)
    db_session.commit()
    db_session.refresh(new_guest)
    
    # 4. Сохраняем UID карты и ID "нового" гостя в context для шага 'When'.
    context['taken_card_uid'] = card_uid
    context['new_guest_id'] = new_guest.guest_id

    print(f"\n[GIVEN] Карта '{card_uid}' привязана к гостю {owner_guest.guest_id}. Создан новый гость {new_guest.guest_id}.")

@when("Клиент пытается привязать эту карту к новому гостю")
def when_attempt_to_assign_taken_card(client, context: dict):
    """
    Шаг выполнения: отправляет запрос на привязку уже занятой карты
    к другому (новому) гостю.
    """
    access_token = context.get("access_token")
    card_uid = context.get("taken_card_uid")
    guest_id = context.get("new_guest_id")
    assert all([access_token, card_uid, guest_id]), "Необходимые данные (токен, UID карты, ID гостя) не найдены в context."

    url = f"/api/guests/{guest_id}/cards"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"card_uid": card_uid}

    print(f"[WHEN] Попытка привязать карту '{card_uid}' к новому гостю '{guest_id}'.")
    response = client.post(url, headers=headers, json=payload)
    context['response'] = response

@when(parsers.parse("Клиент отправляет POST-запрос на /api/guests/{несуществующий_uuid}/topup"))
def attempt_topup_for_nonexistent_guest(client, context: dict):
    """
    Отправляет запрос на пополнение баланса для заведомо несуществующего UUID гостя.
    """
    access_token = context.get("access_token")
    assert access_token, "Токен доступа не найден в context."
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Генерируем случайный, валидный по формату, но гарантированно
    #    несуществующий в тестовой БД UUID.
    non_existent_uuid = uuid.uuid4()
    url = f"/api/guests/{non_existent_uuid}/topup"
    
    # 2. Тело запроса должно быть валидным, так как мы проверяем
    #    обработку URL, а не данных.
    payload = {"amount": 100.00, "payment_method": "cash"}

    shift_open = client.post("/api/shifts/open", headers=headers)
    assert shift_open.status_code in (200, 409)

    print(f"\n[WHEN] Попытка пополнить баланс для несуществующего гостя UUID: {non_existent_uuid}")
    response = client.post(url, headers=headers, json=payload)
    context['response'] = response

@given("У гостя есть пополнение и налив")
def create_guest_with_mixed_history(db_session: Session, context: dict):
    """
    Шаг подготовки: создает полную инфраструктуру для гостя,
    включая запись о наливе (pour) и запись о пополнении (topup)
    с разными временными метками для проверки сортировки.
    """
    # 1. Создаем гостя, карту, напиток, кегу и кран.
    guest = Guest(
        last_name="Историев", first_name="Алексей",
        phone_number=f"+7966{uuid.uuid4().hex[:7]}",
        date_of_birth=date(1990, 5, 15),  # Добавлено
        id_document=f"6666 {uuid.uuid4().hex[:6]}",  # Добавлено
        balance=Decimal("1000.00")
    )
    card = Card(card_uid=f"HISTORY-CARD-{uuid.uuid4().hex[:6]}", guest=guest, status="active")
    beverage = Beverage(
        name=f"HistoryBeer-{uuid.uuid4()}",
        brewery="BDD Brewery",
        style="Pilsner",
        abv=Decimal("4.8"),
        sell_price_per_liter=Decimal("400.00")
    )
    keg = Keg(
        beverage=beverage,
        initial_volume_ml=50000,
        current_volume_ml=40000,
        purchase_price=Decimal("5000.00"),  # Добавлено
        status="in_use"
    )
    tap = Tap(display_name=f"HistoryTap-{uuid.uuid4()}", keg=keg, status="active")
    db_session.add_all([guest, card, beverage, keg, tap])
    db_session.commit()
    db_session.refresh(guest)

    # 2. Создаем запись о наливе, который произошел "в прошлом" (час назад).
    pour_time = datetime.now(timezone.utc) - timedelta(hours=1)
    pour = models.Pour(
        client_tx_id=f"history-pour-{uuid.uuid4()}",  # Добавлено
        guest_id=guest.guest_id, card_uid=card.card_uid, tap_id=tap.tap_id, keg_id=keg.keg_id,
        volume_ml=500,
        amount_charged=Decimal("200.00"),
        price_per_ml_at_pour=Decimal("0.4000"),
        poured_at=pour_time,
    )
    db_session.add(pour)

    # 3. Создаем запись о пополнении, которое произошло "сейчас".
    topup = Transaction(
        guest_id=guest.guest_id, amount=Decimal("500.00"),
        type="topup", payment_method="cash"
    )
    db_session.add(topup)
    
    db_session.commit()

    # 4. Сохраняем ID гостя для шага 'When'.
    context['guest_id'] = guest.guest_id
    print(f"\n[GIVEN] Создан гость {guest.guest_id} с наливом ({pour_time}) и пополнением (now).")


@when("Клиент отправляет GET-запрос на /api/guests/{guest_id}/history")
def get_guest_history(client, context: dict):
    """
    Отправляет запрос на получение истории операций для гостя.
    """
    access_token = context.get("access_token")
    guest_id = context.get("guest_id")
    assert access_token and guest_id, "Необходимые данные не найдены в context."
    headers = {"Authorization": f"Bearer {access_token}"}

    url = f"/api/guests/{guest_id}/history"
    print(f"\n[WHEN] Отправка GET-запроса на {url}")
    response = client.get(url, headers=headers)
    context["response"] = response


@then("Тело ответа должно содержать отсортированный список из двух операций")
def check_history_response(context: dict):
    """
    Проверяет, что ответ содержит объект с ключом 'history',
    в котором находится список из двух элементов, отсортированный
    по времени в порядке убывания.
    """
    response_json = context["response"].json()
    
    # 1. Проверяем, что тело ответа - это словарь и содержит ключ 'history'.
    assert isinstance(response_json, dict), f"Тело ответа не является словарем. Получено: {type(response_json)}"
    assert "history" in response_json, "В теле ответа отсутствует ключ 'history'."
    
    history_list = response_json["history"]
    
    # 2. Проверяем, что значение по ключу 'history' - это список.
    assert isinstance(history_list, list), f"Значение по ключу 'history' не является списком. Получено: {type(history_list)}"
    
    # 3. Проверяем, что в списке ровно две операции.
    assert len(history_list) == 2, f"Ожидалось 2 операции в истории, получено: {len(history_list)}"
    print("[THEN] В истории найдено 2 операции.")

    # 4. Проверяем, что операции отсортированы (от новых к старым).
    timestamp1 = datetime.fromisoformat(history_list[0]['timestamp'])
    timestamp2 = datetime.fromisoformat(history_list[1]['timestamp'])
    assert timestamp1 > timestamp2, "Операции в истории не отсортированы по убыванию времени."
    print(f"[THEN] Сортировка корректна: {timestamp1} > {timestamp2}.")

    # 5. Проверяем, что типы операций разные.
    types = {op['type'] for op in history_list}
    assert "topup" in types and "pour" in types, f"В истории отсутствуют необходимые типы операций. Найдены: {types}"
    print("[THEN] В истории присутствуют и 'topup', и 'pour'.")

