# backend/tests/step_defs/test_security_steps.py

from pytest_bdd import scenarios, when, then, parsers
from httpx import Response
from sqlalchemy.orm import Session
from models import AuditLog

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