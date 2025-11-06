# backend/tests/step_defs/test_inventory_taps_steps.py

import uuid
from pytest_bdd import scenarios, given, when, parsers, then
from sqlalchemy.orm import Session
import models
from models import Keg, Tap

# Этот файл связывает inventory_taps.feature с нашим тестовым фреймворком.
# Все шаги для сценария TC-API-INV-01 уже реализованы или будут реализованы
# в общем файле conftest.py
scenarios('../features/inventory_taps.feature')

@given(parsers.parse('Существует напиток с названием "{name}"'))
def create_existing_beverage(client, db_session: Session, name: str, context: dict):
    """
    Шаг подготовки: создает в БД напиток с указанным названием.
    """
    beverage_data = {
        "name": name,
        "brewery": "Test Factory",
        "style": "Generic",
        "abv": "6.0",
        "sell_price_per_liter": "400.00"
    }
    beverage = models.Beverage(**beverage_data)
    db_session.add(beverage)
    db_session.commit()
    
    # Сохраняем название для использования в следующем шаге
    context['duplicate_beverage_name'] = name
    print(f"\n[GIVEN] Создан напиток с названием '{name}' для теста на дублирование.")

@when("Клиент пытается создать новый напиток с тем же названием")
def attempt_to_create_duplicate_beverage(client, context: dict):
    """
    Шаг выполнения: пытается создать второй напиток с тем же названием.
    """
    access_token = context.get("access_token")
    name = context.get('duplicate_beverage_name')
    assert access_token and name, "Необходимые данные не найдены в context."

    headers = {"Authorization": f"Bearer {access_token}"}
    # Используем другие данные, но то же самое имя
    payload = {
        "name": name,
        "brewery": "Another Brewery",
        "style": "IPA",
        "abv": "7.5",
        "sell_price_per_liter": "550.00"
    }
    
    print(f"[WHEN] Попытка создать напиток с уже существующим названием '{name}'.")
    response = client.post("/api/beverages/", headers=headers, json=payload)
    context['response'] = response

@given(parsers.parse('Существует напиток "{name}"'))
def create_beverage_for_keg_test(client, db_session: Session, name: str, context: dict):
    """
    Шаг подготовки: создает напиток и сохраняет его ID для создания кеги.
    """
    beverage_data = {
        "name": name, "brewery": "BDD Kegs", "style": "Pilsner",
        "abv": "4.8", "sell_price_per_liter": "300.00"
    }
    beverage = models.Beverage(**beverage_data)
    db_session.add(beverage)
    db_session.commit()
    db_session.refresh(beverage) # Получаем ID из БД
    
    context['beverage_id'] = beverage.beverage_id
    print(f"\n[GIVEN] Создан напиток '{name}' с ID {beverage.beverage_id}.")

@when("Клиент отправляет POST-запрос на /api/kegs/ с данными для этой кеги")
def create_new_keg(client, context: dict):
    """
    Шаг выполнения: создает новую кегу, привязанную к напитку из шага Given.
    """
    access_token = context.get("access_token")
    beverage_id = context.get("beverage_id")
    assert access_token and beverage_id, "Необходимые данные не найдены в context."

    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "beverage_id": str(beverage_id), # UUID нужно передавать как строку
        "initial_volume_ml": 50000,
        "purchase_price": "5000.00"
    }
    
    print(f"[WHEN] Попытка создать кегу с привязкой к напитку {beverage_id}.")
    response = client.post("/api/kegs/", headers=headers, json=payload)
    context['response'] = response
    # Сохраняем ID напитка для проверки в БД
    context['keg_check_beverage_id'] = beverage_id

@then(parsers.parse('В таблице "kegs" должна появиться новая запись со статусом "{status}"'))
def check_keg_table_for_new_record(db_session: Session, status: str, context: dict):
    """
    Шаг проверки: находит кегу и проверяет ее статус и привязку к напитку.
    """
    beverage_id = context.get('keg_check_beverage_id')
    assert beverage_id, "ID напитка для проверки кеги не найден в context."

    # Находим кеги, привязанные к нашему напитку
    kegs = db_session.query(Keg).filter(Keg.beverage_id == beverage_id).all()

    assert len(kegs) > 0, f"В БД не найдено ни одной кеги для напитка {beverage_id}."
    
    # Берем последнюю созданную кегу (на случай если их будет несколько)
    new_keg = kegs[-1]
    
    print(f"[THEN] Проверка кеги. Ожидаемый статус: '{status}', фактический: '{new_keg.status}'.")
    assert new_keg.status == status, "Статус кеги в БД не соответствует ожидаемому."
    print(f"[THEN] Кега успешно найдена, статус '{status}' корректен.")

@given('Кега имеет статус "in_use"')
def create_keg_in_use(client, db_session: Session, context: dict):
    """
    Шаг подготовки: создает полную цепочку (Напиток -> Кега -> Кран),
    чтобы кега получила статус 'in_use'.
    """
    # 1. Создаем напиток
    beverage = models.Beverage(
        name="Special Keg Beer", brewery="BDD Factory", style="Ale",
        abv="6.5", sell_price_per_liter="500.00"
    )
    db_session.add(beverage)
    db_session.commit()
    db_session.refresh(beverage)
    
    # 2. Создаем кегу
    keg = Keg(beverage_id=beverage.beverage_id, initial_volume_ml=30000,
              current_volume_ml=30000, purchase_price="4000", status="full")
    db_session.add(keg)
    db_session.commit()
    db_session.refresh(keg)
    
    # 3. Создаем кран
    tap = Tap(display_name="Tap for Deletion Test")
    db_session.add(tap)
    db_session.commit()
    db_session.refresh(tap)
    
    # 4. "Устанавливаем" кегу на кран, меняя статусы
    keg.status = "in_use"
    tap.keg_id = keg.keg_id
    db_session.commit()
    
    # 5. Сохраняем ID кеги для WHEN-шага
    context['keg_id'] = keg.keg_id
    print(f"\n[GIVEN] Создана кега {keg.keg_id} со статусом 'in_use', установленная на кран {tap.tap_id}.")

@when(parsers.parse("Клиент отправляет DELETE-запрос на /api/kegs/{keg_id}"))
def attempt_to_delete_keg(client, context: dict):
    """
    Шаг выполнения: пытается удалить кегу по ID из context.
    """
    access_token = context.get("access_token")
    keg_id = context.get("keg_id")
    assert access_token and keg_id, "Необходимые данные не найдены в context."

    url = f"/api/kegs/{keg_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print(f"[WHEN] Попытка удалить используемую кегу. DELETE-запрос на {url}")
    response = client.delete(url, headers=headers)
    context['response'] = response

@when("Клиент отправляет POST-запрос на /api/taps/ с display_name")
def create_new_tap(client, context: dict):
    """
    Шаг выполнения: создает новый кран.
    """
    access_token = context.get("access_token")
    assert access_token, "Токен доступа не найден."

    headers = {"Authorization": f"Bearer {access_token}"}
    # Используем уникальное имя для каждого запуска теста, чтобы избежать конфликтов
    tap_name = f"Test Tap BDD {uuid.uuid4()}"
    payload = {"display_name": tap_name}
    context['tap_name'] = tap_name # Сохраняем для проверки в БД
    
    print(f"[WHEN] Попытка создать кран с названием '{tap_name}'.")
    response = client.post("/api/taps/", headers=headers, json=payload)
    context['response'] = response

@then(parsers.parse('В таблице "taps" должна появиться новая запись со статусом "{status}"'))
def check_tap_table_for_new_record(db_session: Session, status: str, context: dict):
    """
    Шаг проверки: находит кран по имени и проверяет его статус.
    """
    tap_name = context.get('tap_name')
    assert tap_name, "Имя крана для проверки не найдено в context."

    db_tap = db_session.query(Tap).filter(Tap.display_name == tap_name).one_or_none()

    assert db_tap is not None, f"В БД не найден кран с именем '{tap_name}'."
    
    print(f"[THEN] Проверка крана '{tap_name}'. Ожидаемый статус: '{status}', фактический: '{db_tap.status}'.")
    assert db_tap.status == status, "Статус крана в БД не соответствует ожидаемому."
    print(f"[THEN] Кран успешно найден, статус '{status}' корректен.")

@given('Существует кега со статусом "full" и кран со статусом "locked"')
def create_keg_and_tap_for_assignment(client, db_session: Session, context: dict):
    """
    Шаг подготовки: создает кегу и кран для теста их связывания.
    """
    # 1. Создаем напиток (необходим для кеги)
    beverage = models.Beverage(name=f"BeerToAssign-{uuid.uuid4()}", brewery="BDD Factory", style="Stout", abv="8.0", sell_price_per_liter="600")
    db_session.add(beverage)
    db_session.commit()
    db_session.refresh(beverage)
    
    # 2. Создаем кегу
    keg = Keg(beverage_id=beverage.beverage_id, initial_volume_ml=50000, current_volume_ml=50000, purchase_price="6000", status="full")
    db_session.add(keg)
    db_session.commit()
    db_session.refresh(keg)
    
    # 3. Создаем кран
    tap = Tap(display_name=f"TapToAssign-{uuid.uuid4()}", status="locked")
    db_session.add(tap)
    db_session.commit()
    db_session.refresh(tap)
    
    # 4. Сохраняем ID в context
    context['keg_id_to_assign'] = keg.keg_id
    context['tap_id_to_assign'] = tap.tap_id
    print(f"\n[GIVEN] Создана кега {keg.keg_id} (full) и кран {tap.tap_id} (locked).")

@when("Клиент отправляет PUT-запрос на /api/taps/{tap_id}/keg с id кеги")
def assign_keg_to_tap(client, context: dict):
    """
    Шаг выполнения: отправляет запрос на установку кеги на кран.
    """
    access_token = context.get("access_token")
    keg_id = context.get("keg_id_to_assign")
    tap_id = context.get("tap_id_to_assign")
    assert all([access_token, keg_id, tap_id]), "Необходимые данные не найдены в context."

    url = f"/api/taps/{tap_id}/keg"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"keg_id": str(keg_id)}
    
    print(f"[WHEN] Отправка PUT-запроса на {url} для установки кеги {keg_id}")
    response = client.put(url, headers=headers, json=payload)
    context['response'] = response

@then(parsers.parse('Статус крана должен стать "{expected_status}"'))
def check_tap_status(db_session: Session, expected_status: str, context: dict):
    """
    Шаг проверки: проверяет статус крана после операции.
    """
    tap_id = context.get("tap_id_to_assign")
    assert tap_id, "ID крана не найден в context."
    
    db_tap = db_session.query(Tap).filter(Tap.tap_id == tap_id).one()
    
    print(f"[THEN] Проверка статуса крана {tap_id}. Ожидаемый: '{expected_status}', Фактический: '{db_tap.status}'.")
    assert db_tap.status == expected_status, "Статус крана не обновился корректно."
    print(f"[THEN] Статус крана '{expected_status}' подтвержден.")

@then(parsers.parse('Статус кеги должен стать "{expected_status}"'))
def check_keg_status(db_session: Session, expected_status: str, context: dict):
    """
    Шаг проверки: проверяет статус кеги после операции.
    """
    keg_id = context.get("keg_id_to_assign")
    assert keg_id, "ID кеги не найден в context."
    
    db_keg = db_session.query(Keg).filter(Keg.keg_id == keg_id).one()
    
    print(f"[THEN] Проверка статуса кеги {keg_id}. Ожидаемый: '{expected_status}', Фактический: '{db_keg.status}'.")
    assert db_keg.status == expected_status, "Статус кеги не обновился корректно."
    print(f"[THEN] Статус кеги '{expected_status}' подтвержден.")

@given("Кран уже занят другой кегой")
def create_occupied_tap(client, db_session: Session, context: dict):
    """
    Шаг подготовки: создает полную цепочку (Напиток -> Кега -> Кран),
    чтобы кран получил статус "занят".
    """
    # Этот шаг почти идентичен 'create_keg_in_use', но мы акцентируемся на кране
    # и создаем "лишнюю" кегу для попытки назначения.
    
    # 1. Создаем цепочку для "занятого" крана
    beverage1 = models.Beverage(name=f"OccupyingBeer-{uuid.uuid4()}", brewery="BDD", style="IPA", abv=7, sell_price_per_liter=700)
    keg1 = Keg(beverage=beverage1, initial_volume_ml=50000, current_volume_ml=50000, purchase_price=7000, status="full")
    tap = Tap(display_name=f"OccupiedTap-{uuid.uuid4()}", status="locked")
    db_session.add_all([beverage1, keg1, tap])
    db_session.commit()
    
    tap.keg_id = keg1.keg_id
    keg1.status = "in_use"
    db_session.commit()
    
    # 2. Создаем "лишнюю" кегу, которую будем пытаться назначить
    beverage2 = models.Beverage(name=f"ExtraBeer-{uuid.uuid4()}", brewery="BDD", style="Lager", abv=5, sell_price_per_liter=500)
    keg2 = Keg(beverage=beverage2, initial_volume_ml=30000, current_volume_ml=30000, purchase_price=3000, status="full")
    db_session.add_all([beverage2, keg2])
    db_session.commit()
    
    context['occupied_tap_id'] = tap.tap_id
    context['extra_keg_id'] = keg2.keg_id
    print(f"\n[GIVEN] Кран {tap.tap_id} занят кегой {keg1.keg_id}. Подготовлена кега {keg2.keg_id} для назначения.")

@when("Клиент пытается назначить на него другую кегу")
def attempt_to_assign_to_occupied_tap(client, context: dict):
    access_token = context.get("access_token")
    tap_id = context.get("occupied_tap_id")
    keg_id = context.get("extra_keg_id")
    assert all([access_token, tap_id, keg_id]), "Необходимые данные не найдены."

    url = f"/api/taps/{tap_id}/keg"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"keg_id": str(keg_id)}
    
    print(f"[WHEN] Попытка назначить кегу {keg_id} на занятый кран {tap_id}.")
    response = client.put(url, headers=headers, json=payload)
    context['response'] = response

@when("Клиент пытается назначить эту кегу на другой кран")
def attempt_to_assign_used_keg(client, db_session: Session, context: dict):
    access_token = context.get("access_token")
    keg_id = context.get("keg_id") # Этот ID кеги со статусом 'in_use' мы получили из шага 'Дано'
    assert access_token and keg_id, "Необходимые данные не найдены."

    # Создаем новый, свободный кран
    other_tap = Tap(display_name=f"OtherTap-{uuid.uuid4()}", status="locked")
    db_session.add(other_tap)
    db_session.commit()
    db_session.refresh(other_tap)

    url = f"/api/taps/{other_tap.tap_id}/keg"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"keg_id": str(keg_id)}
    
    print(f"[WHEN] Попытка назначить кегу {keg_id} (in_use) на другой кран {other_tap.tap_id}.")
    response = client.put(url, headers=headers, json=payload)
    context['response'] = response

@given("К крану привязана кега")
def create_tap_with_keg(client, db_session: Session, context: dict):
    """
    Шаг подготовки: создает кран с привязанной к нему кегой.
    """
    # Этот шаг идентичен 'create_keg_in_use', но мы явно сохраняем ID обеих сущностей
    # для последующих шагов.
    
    # 1. Создаем напиток, кегу, кран
    beverage = models.Beverage(name=f"BeerToUnassign-{uuid.uuid4()}", brewery="BDD", style="Porter", abv=6, sell_price_per_liter=650)
    keg = Keg(beverage=beverage, initial_volume_ml=30000, current_volume_ml=30000, purchase_price=4500, status="full")
    tap = Tap(display_name=f"TapToUnassign-{uuid.uuid4()}", status="locked")
    db_session.add_all([beverage, keg, tap])
    db_session.commit()
    
    # 2. "Устанавливаем" кегу на кран
    tap.keg_id = keg.keg_id
    keg.status = "in_use"
    db_session.commit()
    db_session.refresh(tap)
    db_session.refresh(keg)
    
    # 3. Сохраняем ID для следующих шагов
    context['tap_id_to_assign'] = tap.tap_id
    context['keg_id_to_assign'] = keg.keg_id
    print(f"\n[GIVEN] Кран {tap.tap_id} привязан к кеге {keg.keg_id}.")

@when("Клиент отправляет DELETE-запрос на /api/taps/{tap_id}/keg")
def unassign_keg_from_tap(client, context: dict):
    access_token = context.get("access_token")
    tap_id = context.get("tap_id_to_assign")
    assert access_token and tap_id, "Необходимые данные не найдены."

    url = f"/api/taps/{tap_id}/keg"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print(f"[WHEN] Отправка DELETE-запроса на {url} для снятия кеги.")
    response = client.delete(url, headers=headers)
    context['response'] = response

