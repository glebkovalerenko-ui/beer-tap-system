# backend/tests/step_defs/test_security_steps.py

from pytest_bdd import scenarios, when, then, parsers
from httpx import Response
from sqlalchemy.orm import Session
from models import AuditLog
from datetime import datetime, timedelta, timezone
from jose import jwt

# Указываем, какой feature-файл реализуют шаги из этого файла
scenarios('../features/security.feature')

# --- СПЕЦИФИЧНЫЕ When шаги ---

@when(parsers.parse('Клиент отправляет POST-запрос на {url} с валидными username="{username}" и password="{password}"'))
def send_login_request(client, url: str, username: str, password: str, context: dict):
    payload = {"username": username, "password": password}
    response: Response = client.post(url, data=payload)
    context["response"] = response
    try:
        context["response_json"] = response.json()
    except Exception:
        context["response_json"] = None

@when(parsers.parse("Клиент отправляет GET-запрос на {url} с валидным токеном"))
def send_authorized_get_request(client, url: str, context: dict):
    access_token = context.get("access_token")
    assert access_token is not None, "Токен доступа не найден."
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(url, headers=headers)
    context["response"] = response

@when(parsers.parse("Клиент отправляет GET-запрос на {url} без токена"))
def send_unauthorized_get_request(client, url: str, context: dict):
    response = client.get(url)
    context["response"] = response

@when(parsers.parse("Клиент отправляет GET-запрос на {url} с искаженным токеном"))
def send_invalid_token_get_request(client, url: str, context: dict):
    headers = {"Authorization": "Bearer this.is.not.a.valid.jwt.token"}
    response = client.get(url, headers=headers)
    context["response"] = response

@when(parsers.parse("Клиент отправляет POST-запрос на {url} без токена"))
def send_unauthorized_post_request(client, url: str, context: dict):
    response = client.post(url, json={"data": "some_data"})
    context["response"] = response

# --- СПЕЦИФИЧНЫЕ Then шаги ---

@then(parsers.parse('Тело ответа должно содержать "{key}" и "{key2}"'))
def check_response_body_keys(context, key: str, key2: str):
    response_json = context.get("response_json", {})
    assert key in response_json and key2 in response_json

@then(parsers.parse('Тело ответа должно содержать ошибку "{error_message}"'))
def check_response_for_error_message(context: dict, error_message: str):
    response_json = context.get("response_json", {})
    assert response_json.get("detail") == error_message

@then(parsers.parse('В таблице "{table_name}" должна быть создана новая запись'))
def check_for_new_record_in_table(db_session: Session, table_name: str):
    if table_name == "audit_logs":
        record_count = db_session.query(AuditLog).count()
        assert record_count > 0, f"Ожидалось > 0 записей в '{table_name}', но найдено {record_count}."
    else:
        pytest.fail(f"Проверка для таблицы '{table_name}' не реализована в этом файле.")

@when(parsers.parse('Клиент отправляет POST-запрос на /api/token без поля "{missing_field}"'))
def send_login_request_missing_field(client, context: dict, missing_field: str):
    """
    Отправляет запрос на /api/token с неполными данными,
    где отсутствует одно из обязательных полей (username или password).
    """
    # 1. Начинаем с полного набора данных.
    data = {
        "username": "admin",
        "password": "fake_password"
    }
    
    # 2. Целенаправленно удаляем поле, указанное в Gherkin-сценарии.
    if missing_field in data:
        del data[missing_field]
    else:
        pytest.fail(f"Поле '{missing_field}' для удаления не найдено в эталонных данных.")
        
    # 3. Отправляем запрос. Эндпоинт /token ожидает `x-www-form-urlencoded`,
    #    поэтому используем параметр `data`, а не `json`.
    print(f"\n[WHEN] Отправка запроса на /api/token без поля '{missing_field}'. Данные: {data}")
    response = client.post("/api/token", data=data)
    context["response"] = response

@when("Клиент отправляет GET-запрос на /api/guests/ с токеном, подписанным другим ключом")
def send_request_with_wrong_key_token(client, context: dict):
    """
    Создает валидный по структуре и времени жизни JWT, но подписывает его
    неверным секретным ключом, а затем отправляет с ним запрос.
    """
    # 1. Используем другой ключ, отличный от того, что в security.py
    WRONG_SECRET_KEY = "this-is-a-completely-wrong-secret-key"
    ALGORITHM = "HS256"  # Должен совпадать с серверным
    
    # 2. Создаем payload токена, идентичный тому, что создает сервер
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    token_data = {
        "sub": "admin",  # Имя пользователя, от имени которого мы якобы действуем
        "exp": expire
    }
    
    # 3. Кодируем токен, используя НЕВЕРНЫЙ ключ
    wrong_key_token = jwt.encode(token_data, WRONG_SECRET_KEY, algorithm=ALGORITHM)
    
    # 4. Отправляем запрос с этим поддельным токеном
    headers = {"Authorization": f"Bearer {wrong_key_token}"}
    print("\n[WHEN] Отправка запроса с токеном, подписанным неверным ключом.")
    response = client.get("/api/guests/", headers=headers)
    context["response"] = response

@when("Клиент отправляет POST-запрос на /api/token с JSON-телом")
def send_login_request_with_json(client, context: dict):
    """
    Отправляет запрос на /api/token с валидными данными, но
    в формате application/json вместо ожидаемого x-www-form-urlencoded.
    """
    # 1. Данные для входа валидны.
    payload = {
        "username": "admin",
        "password": "fake_password"
    }
    
    # 2. Отправляем запрос, используя параметр `json`, который автоматически
    #    установит заголовок Content-Type: application/json.
    print("\n[WHEN] Отправка запроса на /api/token с Content-Type: application/json.")
    response = client.post("/api/token", json=payload)
    context["response"] = response