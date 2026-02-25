# backend/tests/conftest.py

import pytest
import os
from fastapi.testclient import TestClient
from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import Response
from pytest_bdd import given, when, then, parsers
import models

# Импортируем ключевые компоненты нашего приложения
from main import app
from database import Base, get_db, DATABASE_URL

# =============================================================================
# === Секция 1: Конфигурация тестовой среды и фикстуры Pytest ===
# =============================================================================

USE_POSTGRES = os.getenv("TEST_USE_POSTGRES", "").strip().lower() in {"1", "true", "yes"}
if USE_POSTGRES:
    engine = create_engine(DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client(db_session: Session): # Добавляем зависимость от db_session
    # Логика создания/удаления таблиц теперь в db_session,
    # поэтому здесь она больше не нужна.
    # Зависимость от db_session гарантирует, что БД будет готова.
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def context():
    return {}

@pytest.fixture(scope="function")
def db_session():
    # Создаем все таблицы перед началом теста
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Удаляем все таблицы после завершения теста
        Base.metadata.drop_all(bind=engine)

class SyncBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        func(*args, **kwargs)

def override_background_tasks() -> SyncBackgroundTasks:
    return SyncBackgroundTasks()

app.dependency_overrides[BackgroundTasks] = override_background_tasks

# =============================================================================
# === Секция 2: Общие, переиспользуемые шаги Pytest-BDD ===
# =============================================================================

# --- ОБЩИЕ Given шаги ---

@given("Администратор авторизован")
def administrator_is_authorized(client, context: dict):
    payload = {"username": "admin", "password": "fake_password"}
    print(f"\n[AUTH] Авторизация администратора...")
    response = client.post("/api/token", data=payload)
    assert response.status_code == 200, "Не удалось авторизоваться для выполнения шага 'Дано'."
    response_json = response.json()
    access_token = response_json["access_token"]
    context["access_token"] = access_token
    print(f"[AUTH] Успешно. Токен сохранен.")

@given("Система готова к аутентификации")
def system_ready_for_auth(client):
    assert client is not None
    print("\n[INFO] Система готова к аутентификации.")

@given("Клиент неавторизован")
def client_is_unauthorized(context: dict):
    context.pop("access_token", None)
    print("\n[INFO] Начальное состояние: Клиент неавторизован.")

# --- ОБЩИЕ When шаги ---

@when(parsers.parse("Клиент отправляет POST-запрос на {url} с валидными данными"))
def send_post_with_valid_data(client, url: str, context: dict):
    """
    Универсальный шаг для отправки POST-запроса с валидными данными.
    Определяет, какой payload использовать, на основе URL.
    """
    access_token = context.get("access_token")
    assert access_token is not None, "Токен доступа не найден."
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    
    payload = {}
    if "/api/guests/" in url:
        # Payload для создания гостя
        payload = {
            "last_name": "Гостев", "first_name": "Тест", "patronymic": "Финансович",
            "phone_number": "+79112223344", "date_of_birth": "1995-11-20", "id_document": "2222 333444"
        }
        context['guest_payload'] = payload
    elif "/api/beverages/" in url:
        # Payload для создания напитка
        payload = {
            "name": "Test Lager BDD",
            "brewery": "Pytest Brewery",
            "style": "Lager",
            "abv": "5.2",
            "sell_price_per_liter": "350.00"
        }
        context['beverage_payload'] = payload
    else:
        pytest.fail(f"Не определены валидные данные для POST-запроса на URL: {url}")

    print(f"\n[INFO] Отправка POST-запроса на {url} с данными: {payload}")
    response = client.post(url, headers=auth_headers, json=payload)
    
    context["response"] = response
    try:
        context["response_json"] = response.json()
    except Exception:
        context["response_json"] = None
    print(f"[INFO] Получен ответ: Статус={response.status_code}")

# --- ОБЩИЕ Then шаги ---

@then(parsers.parse('API должен вернуть ответ с кодом {status_code:d}'))
def check_response_code(context, status_code: int):
    response = context.get("response")
    assert response is not None, "Ответ от API не был сохранен в context."
    print(f"[INFO] Проверка кода ответа: Ожидается={status_code}, Получено={response.status_code}")
    assert response.status_code == status_code, f"Ожидался код {status_code}, но получен {response.status_code}"

@then(parsers.parse('В таблице "{table_name}" НЕ должно быть создано новых записей'))
def check_for_no_new_records_in_table(db_session: Session, table_name: str):
    print(f"[INFO] Проверка отсутствия записей в таблице '{table_name}'.")
    if table_name == "audit_logs":
        record_count = db_session.query(models.AuditLog).count()
        assert record_count == 0, f"Ожидалось 0 записей в '{table_name}', но найдено {record_count}."
        print(f"[INFO] В таблице '{table_name}' 0 записей. Проверка успешна.")
    else:
        pytest.fail(f"Проверка для таблицы '{table_name}' еще не реализована.")

@then(parsers.parse('В таблице "{table_name}" должна появиться новая запись'))
def check_table_for_new_record(db_session: Session, table_name: str, context: dict):
    """
    Проверяет, что в указанной таблице была создана запись.
    Работает для 'guests', 'transactions', 'beverages' и 'controllers'.
    """
    print(f"[INFO] Проверка наличия новой записи в таблице '{table_name}'.")
    
    if table_name == "guests":
        # ... (существующий код без изменений)
        guest_payload = context.get('guest_payload')
        assert guest_payload is not None, "Данные для проверки гостя не найдены в context."
        phone_number = guest_payload['phone_number']
        db_guest = db_session.query(models.Guest).filter(models.Guest.phone_number == phone_number).one_or_none()
        assert db_guest is not None, f"Гость с номером телефона {phone_number} не был найден в БД."
        print(f"[INFO] Гость с телефоном {phone_number} успешно найден в БД.")

    elif table_name == "transactions":
        # ... (существующий код без изменений)
        guest_id = context.get('guest_id')
        assert guest_id is not None, "ID гостя не найден для проверки транзакции."
        count = db_session.query(models.Transaction).filter(models.Transaction.guest_id == guest_id).count()
        assert count > 0, f"Для гостя {guest_id} не найдено ни одной транзакции в БД."
        print(f"[INFO] Найдено {count} транзакций для гостя. Проверка пройдена.")
        
    elif table_name == "beverages":
        # ... (существующий код без изменений)
        beverage_payload = context.get('beverage_payload')
        assert beverage_payload is not None, "Данные для проверки напитка не найдены в context."
        name = beverage_payload['name']
        db_beverage = db_session.query(models.Beverage).filter(models.Beverage.name == name).one_or_none()
        assert db_beverage is not None, f"Напиток с названием '{name}' не был найден в БД."
        print(f"[INFO] Напиток '{name}' успешно найден в БД.")

    elif table_name == "controllers":
        controller_id = context.get('controller_id')
        assert controller_id is not None, "ID контроллера для проверки не найден в context."
        db_controller = db_session.query(models.Controller).filter(models.Controller.controller_id == controller_id).one_or_none()
        assert db_controller is not None, f"Контроллер с ID '{controller_id}' не был найден в БД."
        print(f"[INFO] Контроллер '{controller_id}' успешно найден в БД.")
        
    else:
        pytest.fail(f"Проверка для таблицы '{table_name}' не реализована.")
