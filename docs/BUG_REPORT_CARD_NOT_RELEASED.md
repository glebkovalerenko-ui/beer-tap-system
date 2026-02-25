# Баг-репорт: Карта не освобождается после закрытия визита

## Описание проблемы

После закрытия визита карта остаётся привязанной к гостю и не может быть использована другим гостем или в другом визите, что блокирует повторное использование карт.

## Шаги воспроизведения

### 1. Подготовка окружения
```bash
docker compose down -v
docker compose up -d postgres
docker compose run --rm beer_backend_api alembic upgrade head
docker compose up -d beer_backend_api
```

### 2. API сценарий

#### A) Создать гостя G1
```bash
POST /api/guests
Authorization: Bearer <token>
Content-Type: application/json

{
  "last_name": "Testov",
  "first_name": "Test", 
  "patronymic": "Testovich",
  "phone_number": "1111111111",
  "date_of_birth": "1990-01-01",
  "id_document": "PASS123456"
}
```

**Ответ:** `201 Created`
```json
{
  "last_name":"Testov",
  "first_name":"Test",
  "patronymic":"Testovich",
  "phone_number":"1111111111",
  "date_of_birth":"1990-01-01",
  "id_document":"PASS123456",
  "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
  "balance":0.00,
  "is_active":true,
  "created_at":"2026-02-23T09:04:12.345678Z",
  "updated_at":"2026-02-23T09:04:12.345678Z"
}
```

#### B) Открыть визит V1 без карты
```bash
POST /api/visits/open
Authorization: Bearer <token>
Content-Type: application/json

{
  "guest_id": "a6d82e91-8918-4a0b-b532-3de2ad5507ff"
}
```

**Ответ:** `200 OK`
```json
{
  "visit_id":"aa824185-4de8-4dc3-bb01-485b9ecd63c0",
  "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
  "card_uid":null,
  "status":"active",
  "opened_at":"2026-02-23T09:04:17.095093Z",
  "closed_at":null,
  "closed_reason":null,
  "active_tap_id":null,
  "card_returned":true
}
```

#### C) Создать карту C1
```bash
POST /api/cards/
Authorization: Bearer <token>
Content-Type: application/json

{
  "card_uid": "TEST_CARD_UID_001"
}
```

**Ответ:** `201 Created`
```json
{
  "card_uid":"TEST_CARD_UID_001",
  "guest_id":null,
  "status":"inactive",
  "created_at":"2026-02-23T09:04:25.791830Z"
}
```

#### D) Привязать карту C1 к гостю G1
```bash
POST /api/guests/a6d82e91-8918-4a0b-b532-3de2ad5507ff/cards
Authorization: Bearer <token>
Content-Type: application/json

{
  "card_uid": "TEST_CARD_UID_001"
}
```

**Ответ:** `200 OK`
```json
{
  "last_name":"Testov",
  "first_name":"Test",
  "patronymic":"Testovich",
  "phone_number":"1111111111",
  "date_of_birth":"1990-01-01",
  "id_document":"PASS123456",
  "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
  "balance":0.00,
  "is_active":true,
  "created_at":"2026-02-23T09:04:12.345678Z",
  "updated_at":"2026-02-23T09:04:29.123456Z",
  "cards":[
    {
      "card_uid":"TEST_CARD_UID_001",
      "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
      "status":"inactive",
      "created_at":"2026-02-23T09:04:25.791830Z"
    }
  ]
}
```

#### E) Assign card C1 к визиту V1
```bash
POST /api/visits/aa824185-4de8-4dc3-bb01-485b9ecd63c0/assign-card
Authorization: Bearer <token>
Content-Type: application/json

{
  "card_uid": "TEST_CARD_UID_001"
}
```

**Ответ:** `200 OK`
```json
{
  "visit_id":"aa824185-4de8-4dc3-bb01-485b9ecd63c0",
  "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
  "card_uid":"TEST_CARD_UID_001",
  "status":"active",
  "opened_at":"2026-02-23T09:04:17.095093Z",
  "closed_at":null,
  "closed_reason":null,
  "active_tap_id":null,
  "card_returned":true
}
```

#### F) Закрыть визит V1
```bash
POST /api/visits/aa824185-4de8-4dc3-bb01-485b9ecd63c0/close
Authorization: Bearer <token>
Content-Type: application/json

{
  "closed_reason": "guest_checkout",
  "card_returned": true
}
```

**Ответ:** `200 OK`
```json
{
  "visit_id":"aa824185-4de8-4dc3-bb01-485b9ecd63c0",
  "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
  "card_uid":"TEST_CARD_UID_001",
  "status":"closed",
  "opened_at":"2026-02-23T09:04:17.095093Z",
  "closed_at":"2026-02-23T09:04:38.152554Z",
  "closed_reason":"guest_checkout",
  "active_tap_id":null,
  "card_returned":true
}
```

#### G) Проверить статус карты у гостя G1
```bash
GET /api/guests/a6d82e91-8918-4a0b-b532-3de2ad5507ff
Authorization: Bearer <token>
```

**Ответ:** `200 OK`
```json
{
  "last_name":"Testov",
  "first_name":"Test",
  "patronymic":"Testovich",
  "phone_number":"1111111111",
  "date_of_birth":"1990-01-01",
  "id_document":"PASS123456",
  "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
  "balance":0.00,
  "is_active":true,
  "created_at":"2026-02-23T09:04:12.345678Z",
  "updated_at":"2026-02-23T09:04:46.789012Z",
  "cards":[
    {
      "card_uid":"TEST_CARD_UID_001",
      "guest_id":"a6d82e91-8918-4a0b-b532-3de2ad5507ff",
      "status":"inactive",
      "created_at":"2026-02-23T09:04:25.791830Z"
    }
  ]
}
```

#### H) Создать гостя G2
```bash
POST /api/guests
Authorization: Bearer <token>
Content-Type: application/json

{
  "last_name": "Petrov",
  "first_name": "Petr",
  "patronymic": "Petrovich", 
  "phone_number": "2222222222",
  "date_of_birth": "1985-05-15",
  "id_document": "PASS789012"
}
```

**Ответ:** `201 Created`
```json
{
  "last_name":"Petrov",
  "first_name":"Petr",
  "patronymic":"Petrovich",
  "phone_number":"2222222222",
  "date_of_birth":"1985-05-15",
  "id_document":"PASS789012",
  "guest_id":"50315d58-34c6-4721-946f-fd79a7beccac",
  "balance":0.00,
  "is_active":true,
  "created_at":"2026-02-23T09:04:48.234567Z",
  "updated_at":"2026-02-23T09:04:48.234567Z"
}
```

#### I) Открыть визит V2 без карты
```bash
POST /api/visits/open
Authorization: Bearer <token>
Content-Type: application/json

{
  "guest_id": "50315d58-34c6-4721-946f-fd79a7beccac"
}
```

**Ответ:** `200 OK`
```json
{
  "visit_id":"2cd38569-2271-412e-994e-69f0e2f55b17",
  "guest_id":"50315d58-34c6-4721-946f-fd79a7beccac",
  "card_uid":null,
  "status":"active",
  "opened_at":"2026-02-23T09:04:52.151612Z",
  "closed_at":null,
  "closed_reason":null,
  "active_tap_id":null,
  "card_returned":true
}
```

#### J) Попробовать привязать карту C1 к гостю G2
```bash
POST /api/guests/50315d58-34c6-4721-946f-fd79a7beccac/cards
Authorization: Bearer <token>
Content-Type: application/json

{
  "card_uid": "TEST_CARD_UID_001"
}
```

**Ответ:** `409 Conflict`
```json
{
  "detail": "Card with UID TEST_CARD_UID_001 is already assigned to another guest."
}
```

#### J2) Попробовать привязать карту C1 к визиту V2
```bash
POST /api/visits/2cd38569-2271-412e-994e-69f0e2f55b17/assign-card
Authorization: Bearer <token>
Content-Type: application/json

{
  "card_uid": "TEST_CARD_UID_001"
}
```

**Ответ:** `409 Conflict`
```json
{
  "detail": "Card is assigned to another guest"
}
```

## Анализ состояния базы данных

### Таблица cards
```sql
SELECT card_uid, guest_id, status, created_at FROM cards WHERE card_uid = 'TEST_CARD_UID_001';
```

**Результат:**
```
     card_uid      |               guest_id               |  status  |          created_at          
-------------------+--------------------------------------+----------+-------------------------------
 TEST_CARD_UID_001 | a6d82e91-8918-4a0b-b532-3de2ad5507ff | inactive | 2026-02-23 09:04:25.79183+00
(1 row)
```

### Таблица visits
```sql
SELECT visit_id, guest_id, card_uid, status, opened_at, closed_at, closed_reason FROM visits WHERE card_uid = 'TEST_CARD_UID_001';
```

**Результат:**
```
                              visit_id                               |               guest_id               |     card_uid      | status |           opened_at           |           closed_at           | closed_reason 
---------------------------------------------------------------------+--------------------------------------+-------------------+--------+-------------------------------+-------------------------------+----------------
 aa824185-4de8-4dc3-bb01-485b9ecd63c0 | a6d82e91-8918-4a0b-b532-3de2ad5507ff | TEST_CARD_UID_001 | closed | 2026-02-23 09:04:17.095093+00 | 2026-02-23 09:04:38.152554+00 | guest_checkout
(1 row)
```

## Анализ проблемы

### Корень проблемы

Проблема находится в функции `close_visit()` в файле `backend/crud/visit_crud.py` (строки 228-249):

```python
def close_visit(db: Session, visit_id: uuid.UUID, closed_reason: str, card_returned: bool):
    # ... код проверки ...
    
    visit.status = "closed"
    visit.closed_reason = closed_reason
    visit.closed_at = datetime.now(timezone.utc)
    visit.card_returned = card_returned
    visit.active_tap_id = None

    if visit.card_uid is not None:
        card = db.query(models.Card).filter(models.Card.card_uid == visit.card_uid).first()
        if card:
            card.status = "inactive"  # <-- ПРОБЛЕМА: только статус меняется

    db.commit()
    db.refresh(visit)
    return visit
```

### Что происходит не так

1. **Карта остаётся привязанной к гостю**: `card.guest_id` не сбрасывается в `NULL`
2. **Статус карты меняется на "inactive"**, но привязка к гостю сохраняется
3. **Проверка в API endpoints блокирует повторное использование**:
   - В `assign_or_register_card_to_guest()` проверяется `card.guest_id != guest_id`
   - В `assign_card_to_active_visit()` проверяется `card.guest_id != visit.guest_id`

### Участствующие таблицы и сущности

1. **cards**: `card_uid`, `guest_id`, `status`
2. **visits**: `visit_id`, `guest_id`, `card_uid`, `status`
3. **guests**: `guest_id` (связь с cards через `guest_id`)

### Ожидаемое поведение

После закрытия визита с параметром `card_returned: true` карта должна:
1. Изменить статус на "inactive"
2. **Сбросить `guest_id` в `NULL`**, освободив её для повторного использования

### Фактическое поведение

Карта:
1. Меняет статус на "inactive" ✓
2. **Остаётся привязанной к гостю** (`guest_id` не меняется) ✗

## Влияние на систему

- **Блокировка повторного использования карт**: Карты не могут быть переданы другим гостям
- **Утечка ресурсов**: Карты "застревают" на гостях навсегда
- **Проблемы с операционной деятельностью**: Невозможно переиспользовать физические карты

## Рекомендуемое исправление

В функции `close_visit()` в `backend/crud/visit_crud.py` добавить сброс `guest_id`:

```python
def close_visit(db: Session, visit_id: uuid.UUID, closed_reason: str, card_returned: bool):
    visit = get_visit(db, visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Visit is already closed")

    visit.status = "closed"
    visit.closed_reason = closed_reason
    visit.closed_at = datetime.now(timezone.utc)
    visit.card_returned = card_returned
    visit.active_tap_id = None

    if visit.card_uid is not None:
        card = db.query(models.Card).filter(models.Card.card_uid == visit.card_uid).first()
        if card:
            card.status = "inactive"
            if card_returned:  # <-- ДОБАВИТЬ ЭТОТ БЛОК
                card.guest_id = None  # Освобождаем карту для повторного использования

    db.commit()
    db.refresh(visit)
    return visit
```

## Вывод

**Баг подтвержден**: Карта не освобождается после закрытия визита, что блокирует её повторное использование. Проблема в том, что при закрытии визита статус карты меняется на "inactive", но привязка к гостю (`guest_id`) не сбрасывается. Это приводит к невозможности использования карты другими гостями или в других визитах.
