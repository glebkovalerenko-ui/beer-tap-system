# backend/tests_system/test_module_03_core_logic.py
import pytest
import subprocess
import os
import time
import requests
import uuid
import json
from datetime import datetime, timezone

# Определение путей
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DOCKER_COMPOSE_PATH = os.path.join(PROJECT_ROOT, 'docker-compose.yml')

pytestmark = pytest.mark.system

def run_docker_compose(args: list[str], **kwargs):
    """Утилита для запуска команд docker-compose."""
    base_command = ["docker-compose", "-f", DOCKER_COMPOSE_PATH]
    kwargs.setdefault('cwd', PROJECT_ROOT)
    return subprocess.run(base_command + args, capture_output=True, text=True, **kwargs)

def run_psql_command(sql: str):
    """
    Утилита для выполнения SQL-команд через psql в контейнере.
    Использует флаги -A -t для чистого, машиночитаемого вывода.
    """
    return run_docker_compose([
        'exec', '-T', 'postgres', 'psql', 
        '-U', 'beer_user', '-d', 'beer_db',
        '-A',  # Убрать выравнивание
        '-t',  # Выводить только кортежи (данные), без заголовков и футеров
        '-c', sql
    ], check=True)

@pytest.fixture(scope="function")
def idempotency_test_environment():
    """
    Подготавливает чистую, рабочую среду для каждого теста идемпотентности.
    Создает все необходимые связанные сущности (гость, кега, кран и т.д.).
    """
    print("\n--- [Test Setup: idempotency_test_environment] ---")
    
    # 1. Полная очистка и запуск
    run_docker_compose(["down", "-v"], check=True)
    run_docker_compose(["up", "-d"], check=True)
    print("Ожидание готовности системы (15 секунд)...")
    time.sleep(15)
    
    # 2. Применение миграций
    print("Применение миграций Alembic...")
    run_docker_compose(['exec', '-T', 'beer_backend_api', 'alembic', 'upgrade', 'head'], check=True)

    # 3. Создание опорных данных
    print("Создание опорных данных в БД...")
    
    beverage_id = str(uuid.uuid4())
    keg_id = str(uuid.uuid4())
    guest_id = str(uuid.uuid4())
    card_uid = f"IDEMPOTENCY-CARD-{uuid.uuid4().hex[:8]}"
    tap_id = 1

    # ИСПРАВЛЕНИЕ: Добавлено поле is_active со значением true в INSERT для guests.
    sql_setup = f"""
        INSERT INTO beverages (beverage_id, name, sell_price_per_liter) 
        VALUES ('{beverage_id}', 'Test Beer', 500.00);
        
        INSERT INTO kegs (keg_id, beverage_id, initial_volume_ml, current_volume_ml, purchase_price, status) 
        VALUES ('{keg_id}', '{beverage_id}', 30000, 30000, 8000.00, 'in_use');
        
        INSERT INTO taps (tap_id, keg_id, display_name, status) 
        VALUES ({tap_id}, '{keg_id}', 'Test Tap 1', 'active');
        
        INSERT INTO guests (guest_id, last_name, first_name, phone_number, date_of_birth, id_document, balance, is_active)
        VALUES ('{guest_id}', 'Idempotentov', 'Test', '+79998887766', '1995-05-05', '5015 123456', 5000.00, true);
        
        INSERT INTO cards (card_uid, guest_id, status) 
        VALUES ('{card_uid}', '{guest_id}', 'active');
    """
    run_psql_command(sql_setup)
    
    print("[OK] Опорные данные созданы.")
    
    yield {
        "tap_id": tap_id,
        "card_uid": card_uid,
    }
    
    print("\n--- [Test Teardown: idempotency_test_environment] ---")
    run_docker_compose(["down", "-v"], check=True)

def test_tc_sys_srv_01_idempotency_duplicate_tx(idempotency_test_environment):
    """Проверяет TC-SYS-SRV-01: Повторная отправка налива с тем же client_tx_id."""
    print("\n[Scenario] TC-SYS-SRV-01: Идемпотентность - дубликат транзакции.")
    
    tap_id = idempotency_test_environment["tap_id"]
    card_uid = idempotency_test_environment["card_uid"]
    client_tx_id = f"TX-{uuid.uuid4().hex}"
    
    pour_data = {
        "client_tx_id": client_tx_id,
        "card_uid": card_uid,
        "tap_id": tap_id,
        "start_ts": datetime.now(timezone.utc).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "volume_ml": 500,
        "price_cents": 25000,
    }
    sync_request_body = {"pours": [pour_data]}

    # === Action 1: Первый запрос ===
    print(f"\n[Action] Отправка первого запроса с client_tx_id: {client_tx_id}")
    response1 = requests.post(
        "http://localhost:8000/api/sync/pours/",
        json=sync_request_body
    )
    
    # === Verification 1: Проверка ответа и БД ===
    assert response1.status_code == 200
    response1_data = response1.json()
    print(f"[Check] Ответ получен: {response1_data}")
    assert response1_data["results"][0]["status"] == "accepted"
    print("[OK] Первый запрос принят успешно.")
    
    # ИСПРАВЛЕНИЕ: Упрощаем парсинг благодаря чистому выводу psql
    psql_count_res1 = run_psql_command(f"SELECT COUNT(*) FROM pours WHERE client_tx_id = '{client_tx_id}';")
    count1 = int(psql_count_res1.stdout.strip())
    assert count1 == 1
    print("[OK] В БД создана 1 запись.")
    
    # === Action 2: Повторный запрос ===
    print(f"\n[Action] Отправка второго (дублирующего) запроса с тем же client_tx_id.")
    response2 = requests.post(
        "http://localhost:8000/api/sync/pours/",
        json=sync_request_body
    )
    
    # === Verification 2: Проверка ответа и БД ===
    assert response2.status_code == 200
    response2_data = response2.json()
    print(f"[Check] Ответ получен: {response2_data}")
    assert response2_data["results"][0]["reason"] == "duplicate"
    print("[OK] Второй запрос распознан как дубликат.")
    
    # ИСПРАВЛЕНИЕ: Упрощаем парсинг
    psql_count_res2 = run_psql_command(f"SELECT COUNT(*) FROM pours WHERE client_tx_id = '{client_tx_id}';")
    count2 = int(psql_count_res2.stdout.strip())
    assert count2 == 1
    print("[OK] В БД по-прежнему 1 запись. Тест пройден.")

@pytest.fixture(scope="function")
def atomicity_test_environment():
    """Подготавливает среду для теста атомарности с двумя гостями."""
    print("\n--- [Test Setup: atomicity_test_environment] ---")
    
    run_docker_compose(["down", "-v"], check=True)
    run_docker_compose(["up", "-d"], check=True)
    time.sleep(15)
    run_docker_compose(['exec', '-T', 'beer_backend_api', 'alembic', 'upgrade', 'head'], check=True)

    print("Создание опорных данных для теста атомарности...")
    
    beverage_id = str(uuid.uuid4())
    keg_id = str(uuid.uuid4())
    guest1_id = str(uuid.uuid4())
    card1_uid = f"ATOM-GOOD-{uuid.uuid4().hex[:8]}"
    guest2_id = str(uuid.uuid4())
    card2_uid = f"ATOM-BAD-{uuid.uuid4().hex[:8]}"
    tap_id = 2

    # ИСПРАВЛЕНИЕ: Добавлено поле purchase_price в INSERT для kegs.
    sql_setup = f"""
        INSERT INTO beverages (beverage_id, name, sell_price_per_liter) VALUES ('{beverage_id}', 'Atomic Beer', 600.00);
        
        INSERT INTO kegs (keg_id, beverage_id, initial_volume_ml, current_volume_ml, purchase_price, status) 
        VALUES ('{keg_id}', '{beverage_id}', 30000, 30000, 9000.00, 'in_use');
        
        INSERT INTO taps (tap_id, keg_id, display_name, status) VALUES ({tap_id}, '{keg_id}', 'Test Tap 2', 'active');
        
        INSERT INTO guests (guest_id, last_name, first_name, phone_number, date_of_birth, id_document, balance, is_active)
        VALUES ('{guest1_id}', 'Rich', 'Test', '+79000000001', '2000-01-01', '1111', 5000.00, true);
        INSERT INTO cards (card_uid, guest_id, status) VALUES ('{card1_uid}', '{guest1_id}', 'active');
        
        INSERT INTO guests (guest_id, last_name, first_name, phone_number, date_of_birth, id_document, balance, is_active)
        VALUES ('{guest2_id}', 'Poor', 'Test', '+79000000002', '2000-01-02', '2222', 10.00, true);
        INSERT INTO cards (card_uid, guest_id, status) VALUES ('{card2_uid}', '{guest2_id}', 'active');
    """
    run_psql_command(sql_setup)
    
    print("[OK] Опорные данные созданы.")
    
    yield {
        "tap_id": tap_id,
        "card_uid_ok": card1_uid,
        "card_uid_fail": card2_uid,
        "guest_id_ok": guest1_id,
        "guest_id_fail": guest2_id,
        "keg_id": keg_id
    }
    
    print("\n--- [Test Teardown: atomicity_test_environment] ---")
    run_docker_compose(["down", "-v"], check=True)


def test_tc_sys_srv_02_atomicity_batch_with_one_fail(atomicity_test_environment):
    """Проверяет TC-SYS-SRV-02: Атомарная обработка пакета с одним валидным и одним невалидным наливом."""
    print("\n[Scenario] TC-SYS-SRV-02: Атомарность - пакет с частичным отказом.")
    
    env = atomicity_test_environment
    pour_volume = 500  # 500 мл
    pour_price = 30000 # 500 мл * 600 руб/л = 300 руб = 30000 центов
    
    # Налив 1 (валидный)
    pour_ok = {
        "client_tx_id": f"TX-OK-{uuid.uuid4().hex}",
        "card_uid": env["card_uid_ok"],
        "tap_id": env["tap_id"],
        "start_ts": datetime.now(timezone.utc).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "volume_ml": pour_volume,
        "price_cents": pour_price,
    }
    
    # Налив 2 (невалидный)
    pour_fail = {
        "client_tx_id": f"TX-FAIL-{uuid.uuid4().hex}",
        "card_uid": env["card_uid_fail"],
        "tap_id": env["tap_id"],
        "start_ts": datetime.now(timezone.utc).isoformat(),
        "end_ts": datetime.now(timezone.utc).isoformat(),
        "volume_ml": pour_volume,
        "price_cents": pour_price,
    }
    
    sync_request_body = {"pours": [pour_ok, pour_fail]}
    
    # === Action ===
    print("[Action] Отправка пакета с одним валидным и одним невалидным наливом...")
    response = requests.post("http://localhost:8000/api/sync/pours/", json=sync_request_body)
    
    # === Verification: API Response ===
    assert response.status_code == 200
    response_data = response.json()
    print(f"[Check] Ответ API получен: {response_data}")
    
    results = {res["client_tx_id"]: res for res in response_data["results"]}
    assert results[pour_ok["client_tx_id"]]["status"] == "accepted"
    assert results[pour_fail["client_tx_id"]]["status"] == "rejected"
    assert "insufficient funds" in results[pour_fail["client_tx_id"]]["reason"].lower()
    print("[OK] Ответ API корректно отражает статусы 'accepted' и 'rejected'.")
    
    # === Verification: Database State ===
    print("[Check] Проверка состояния базы данных...")
    
    # Проверяем записи о наливах
    count_ok = int(run_psql_command(f"SELECT COUNT(*) FROM pours WHERE client_tx_id = '{pour_ok['client_tx_id']}';").stdout.strip())
    count_fail = int(run_psql_command(f"SELECT COUNT(*) FROM pours WHERE client_tx_id = '{pour_fail['client_tx_id']}';").stdout.strip())
    assert count_ok == 1
    assert count_fail == 0
    print("[OK] В БД создана только валидная запись о наливе.")
    
    # Проверяем балансы гостей
    balance_ok = float(run_psql_command(f"SELECT balance FROM guests WHERE guest_id = '{env['guest_id_ok']}';").stdout.strip())
    balance_fail = float(run_psql_command(f"SELECT balance FROM guests WHERE guest_id = '{env['guest_id_fail']}';").stdout.strip())
    assert balance_ok == 5000.00 - (pour_price / 100) # 4700.00
    assert balance_fail == 10.00
    print("[OK] Балансы гостей обновлены корректно.")

    # Проверяем остаток в кеге
    volume_keg = int(run_psql_command(f"SELECT current_volume_ml FROM kegs WHERE keg_id = '{env['keg_id']}';").stdout.strip())
    assert volume_keg == 30000 - pour_volume
    print("[OK] Остаток в кеге обновлен корректно. Тест пройден.")

@pytest.fixture(scope="function")
def audit_test_environment():
    """Подготавливает чистую среду и получает токен аутентификации."""
    print("\n--- [Test Setup: audit_test_environment] ---")
    
    run_docker_compose(["down", "-v"], check=True)
    run_docker_compose(["up", "-d"], check=True)
    time.sleep(15)
    run_docker_compose(['exec', '-T', 'beer_backend_api', 'alembic', 'upgrade', 'head'], check=True)

    print("Получение токена аутентификации...")
    
    # ИСПРАВЛЕНИЕ: Используем правильный пароль 'fake_password' из FAKE_USERS_DB.
    token_payload = {
        "grant_type": "password",
        "username": "admin",
        "password": "fake_password"
    }
    response = requests.post("http://localhost:8000/api/token", data=token_payload)
    response.raise_for_status()
    access_token = response.json()["access_token"]
    
    print("[OK] Токен получен.")
    
    yield { "access_token": access_token }
    
    print("\n--- [Test Teardown: audit_test_environment] ---")
    run_docker_compose(["down", "-v"], check=True)


def test_tc_sys_srv_06_audit_on_create(audit_test_environment):
    """Проверяет TC-SYS-SRV-06: Создание записи в аудите для state-changing операции (POST)."""
    print("\n[Scenario] TC-SYS-SRV-06: Аудит для POST-запроса.")
    
    token = audit_test_environment["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    guest_data = {
        "last_name": "Auditov",
        "first_name": "Test",
        "phone_number": "+79001112233",
        "date_of_birth": "1980-01-01",
        "id_document": "8080 123123"
    }
    
    # === Action ===
    print("[Action] Отправка POST /api/guests/ для создания гостя...")
    response = requests.post("http://localhost:8000/api/guests/", headers=headers, json=guest_data)
    
    # === Verification ===
    assert response.status_code == 201
    guest_id = response.json()["guest_id"]
    print(f"[OK] Гость успешно создан с ID: {guest_id}")
    
    print("[Check] Проверка наличия записи в audit_logs...")
    # Небольшая задержка, чтобы запись успела попасть в БД
    time.sleep(2)
    
    log_entry_raw = run_psql_command(
        f"SELECT actor_id, action, target_entity, target_id FROM audit_logs WHERE action = 'create_guest';"
    ).stdout.strip()
    
    assert log_entry_raw.count('\n') == 0 # Убедимся, что найдена только одна строка
    log_entry = [field.strip() for field in log_entry_raw.split('|')]
    
    assert log_entry[0] == "admin"
    assert log_entry[1] == "create_guest"
    assert log_entry[2] == "Guest"
    assert log_entry[3] == guest_id
    print(f"[OK] Найдена корректная запись в логе аудита: {log_entry}")


def test_tc_sys_srv_07_no_audit_on_get(audit_test_environment):
    """Проверяет TC-SYS-SRV-07: Отсутствие записи в аудите для read-only операции (GET)."""
    print("\n[Scenario] TC-SYS-SRV-07: Отсутствие аудита для GET-запроса.")
    
    token = audit_test_environment["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # === Action ===
    print("[Action] Отправка GET /api/guests/ для получения списка гостей...")
    response = requests.get("http://localhost:8000/api/guests/", headers=headers)
    
    # === Verification ===
    assert response.status_code == 200
    print("[OK] Список гостей получен успешно.")
    
    print("[Check] Проверка отсутствия записей в audit_logs...")
    log_count = int(run_psql_command("SELECT COUNT(*) FROM audit_logs;").stdout.strip())
    
    assert log_count == 0
    print("[OK] Таблица audit_logs пуста, как и ожидалось. Тест пройден.")