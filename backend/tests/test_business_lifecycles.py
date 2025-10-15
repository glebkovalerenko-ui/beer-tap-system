# backend/tests/test_business_lifecycles.py

def test_keg_and_tap_lifecycle(client):
    """
    Тестирует полный сквозной сценарий управления инвентарем:
    1. Аутентификация для получения токена.
    2. Создание сущности "Напиток" (Beverage).
    3. Создание сущности "Кега" (Keg), привязанной к напитку.
    4. Создание сущности "Кран" (Tap).
    5. Назначение Кеги на Кран.
    6. Проверка корректности измененных статусов.
    7. Снятие Кеги с Крана.
    8. Проверка, что статусы вернулись в исходное состояние.
    """
    # --- Шаг 0: Аутентификация ---
    # Мы должны действовать как реальный пользователь, поэтому сначала получаем токен.
    login_response = client.post(
        "/api/token", 
        data={"username": "admin", "password": "fake_password"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- Шаг 1: Создание Напитка (Beverage) ---
    beverage_response = client.post(
        "/api/beverages/", 
        headers=headers, 
        json={"name": "Test Lager", "sell_price_per_liter": 5.50}
    )
    assert beverage_response.status_code == 201
    beverage_id = beverage_response.json()["beverage_id"]

    # --- Шаг 2: Создание Кеги (Keg) ---
    keg_response = client.post(
        "/api/kegs/",
        headers=headers,
        json={
            "beverage_id": beverage_id,
            "initial_volume_ml": 30000,
            "purchase_price": 90.0
        }
    )
    assert keg_response.status_code == 201
    keg_id = keg_response.json()["keg_id"]
    # Проверяем начальный статус
    assert keg_response.json()["status"] == "full"

    # --- Шаг 3: Создание Крана (Tap) ---
    tap_response = client.post(
        "/api/taps/", 
        headers=headers, 
        json={"display_name": "Main Tap"}
    )
    assert tap_response.status_code == 201
    tap_id = tap_response.json()["tap_id"]
    # Проверяем начальный статус
    assert tap_response.json()["status"] == "locked"

    # --- Шаг 4: Назначение Кеги на Кран ---
    assign_response = client.put(
        f"/api/taps/{tap_id}/keg", 
        headers=headers, 
        json={"keg_id": keg_id}
    )
    assert assign_response.status_code == 200
    # Проверяем, что статусы изменились как положено
    assert assign_response.json()["status"] == "active"
    assert assign_response.json()["keg"]["status"] == "in_use"
    assert assign_response.json()["keg"]["keg_id"] == keg_id

    # --- Шаг 5: Снятие Кеги с Крана ---
    unassign_response = client.delete(f"/api/taps/{tap_id}/keg", headers=headers)
    assert unassign_response.status_code == 200
    # Проверяем, что статусы вернулись в безопасное состояние
    assert unassign_response.json()["status"] == "locked"
    assert unassign_response.json()["keg"] is None

    # (Опционально) Проверим статус кеги отдельным запросом, чтобы быть на 100% уверенными
    final_keg_response = client.get(f"/api/kegs/{keg_id}", headers=headers)
    assert final_keg_response.json()["status"] == "full"

def test_guest_and_finance_lifecycle(client):
    """
    Тестирует полный сквозной сценарий управления гостем и его финансами:
    1. Аутентификация.
    2. Создание Гостя.
    3. Регистрация новой Карты.
    4. Привязка Карты к Гостю.
    5. Пополнение баланса Гостя.
    6. Проверка, что баланс корректно обновился.
    """
    # --- Шаг 0: Аутентификация ---
    login_response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- Шаг 1: Создание Гостя ---
    # --- ИЗМЕНЕНИЕ: Добавлены все обязательные поля для успешной валидации ---
    guest_response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": "Doe",
            "first_name": "John",
            "patronymic": "J.",
            "phone_number": "+15551234567",
            "date_of_birth": "1990-05-20",
            "id_document": "PASSPORT 123456"
        }
    )
    assert guest_response.status_code == 201
    guest_id = guest_response.json()["guest_id"]
    # Проверяем начальный баланс
    assert float(guest_response.json()["balance"]) == 0.0

    # --- Шаг 2: Регистрация новой Карты ---
    card_uid = "1122334455"
    card_response = client.post("/api/cards/", headers=headers, json={"card_uid": card_uid})
    assert card_response.status_code == 201
    assert card_response.json()["status"] == "inactive"

    # --- Шаг 3: Привязка Карты к Гостю ---
    assign_response = client.post(
        f"/api/guests/{guest_id}/cards",
        headers=headers,
        json={"card_uid": card_uid}
    )
    assert assign_response.status_code == 200
    # Проверяем, что карта теперь активна
    # --- ИЗМЕНЕНИЕ: Вложенная структура ответа может отличаться, проверяем напрямую гостя ---
    updated_guest = client.get(f"/api/guests/{guest_id}", headers=headers).json()
    assert updated_guest['cards'][0]['status'] == 'active'
    
    # --- Шаг 4: Пополнение баланса Гостя ---
    topup_amount = 50.75
    topup_response = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": topup_amount, "payment_method": "card"}
    )
    assert topup_response.status_code == 200

    # --- Шаг 5: Проверка итогового баланса ---
    # Запрашиваем данные гостя еще раз, чтобы убедиться, что баланс сохранился в БД
    final_guest_response = client.get(f"/api/guests/{guest_id}", headers=headers)
    assert final_guest_response.status_code == 200
    # Сравниваем как float для надежности
    assert float(final_guest_response.json()["balance"]) == topup_amount