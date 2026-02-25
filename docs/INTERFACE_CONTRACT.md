# Interface Contract

**РСЃС‚РѕС‡РЅРёРє правды:** `admin-app/src-tauri/src/lib.rs`, `admin-app/src-tauri/src/main.rs`, `admin-app/src/stores/*.js`, `backend/api/*.py`

**Версия:** 1.0  
**Р”Р°С‚Р°:** 2026-02-17

## Архитектура взаимодействия

```
Svelte 5 Frontend в†ђв†’ Tauri 2.0 (Rust) в†ђв†’ FastAPI Backend
     в†“                    в†“                    в†“
  Stores            Commands          HTTP Endpoints
```

## 1. Таблица маппинга команд

### Authentication & Session

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `sessionStore.setToken()` | `login` | `api_client::login()` | `POST /api/token` (публичный) |

### Guests Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `guestStore.fetchGuests()` | `get_guests` | `api_client::get_guests()` | `GET /api/guests/` (JWT) |
| `guestStore.createGuest()` | `create_guest` | `api_client::create_guest()` | `POST /api/guests/` (JWT) |
| `guestStore.updateGuest()` | `update_guest` | `api_client::update_guest()` | `PUT /api/guests/{id}` (JWT) |
| `guestStore.bindCardToGuest()` | `bind_card_to_guest` | `api_client::bind_card_to_guest()` | `POST /api/guests/{id}/cards` (JWT) |
| `guestStore.topUpBalance()` | `top_up_balance` | `api_client::top_up_balance()` | `POST /api/guests/{id}/topup` (JWT) |

### Kegs Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `kegStore.fetchKegs()` | `get_kegs` | `api_client::get_kegs()` | `GET /api/kegs/` (JWT) |
| `kegStore.createKeg()` | `create_keg` | `api_client::create_keg()` | `POST /api/kegs/` (JWT) |
| `kegStore.updateKeg()` | `update_keg` | `api_client::update_keg()` | `PUT /api/kegs/{id}` (JWT) |
| `kegStore.deleteKeg()` | `delete_keg` | `api_client::delete_keg()` | `DELETE /api/kegs/{id}` (JWT) |

### Taps Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `tapStore.fetchTaps()` | `get_taps` | `api_client::get_taps()` | `GET /api/taps/` (JWT) |
| `tapStore.assignKegToTap()` | `assign_keg_to_tap` | `api_client::assign_keg_to_tap()` | `PUT /api/taps/{id}/keg` (JWT) |
| `tapStore.unassignKegFromTap()` | `unassign_keg_from_tap` | `api_client::unassign_keg_from_tap()` | `DELETE /api/taps/{id}/keg` (JWT) |
| `tapStore.updateTapStatus()` | `update_tap` | `api_client::update_tap()` | `PUT /api/taps/{id}` (JWT) |

### Beverages Management

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `beverageStore.fetchBeverages()` | `get_beverages` | `api_client::get_beverages()` | `GET /api/beverages/` (JWT) |
| `beverageStore.createBeverage()` | `create_beverage` | `api_client::create_beverage()` | `POST /api/beverages/` (JWT) |

### System & Monitoring

| Svelte Store Action | Tauri Command | Rust HTTP Client | FastAPI Endpoint |
|-------------------|---------------|------------------|------------------|
| `systemStore.fetchStatus()` | `get_system_status` | `api_client::get_system_status()` | `GET /api/system/status` (JWT) |
| `systemStore.setEmergencyStop()` | `set_emergency_stop` | `api_client::set_emergency_stop()` | `POST /api/system/emergency_stop` (JWT) |
| `pourStore.fetchPours()` | `get_pours` | `api_client::get_pours()` | `GET /api/pours/` (JWT) |

### NFC Operations (Local only)

| Svelte Store Action | Tauri Command | Rust Implementation | FastAPI Endpoint |
|-------------------|---------------|-------------------|------------------|
| `nfcReaderStore.setupListener()` | `list_readers` | `nfc_handler::list_readers_internal()` | — |
| — | `read_mifare_block` | `nfc_handler::connect_and_authenticate()` | — |
| — | `write_mifare_block` | `nfc_handler::connect_and_authenticate()` | — |
| — | `change_sector_keys` | `nfc_handler::connect_and_authenticate()` | — |

## 2. События NFC: `card-status-changed`

### Основной способ получения данных NFC

**Направление:** Rust в†’ Svelte  
**Механизм:** Tauri Events  
**Частота:** 500ms polling с идемпотентной отправкой

#### Структура payload:

```typescript
interface CardStatusPayload {
  uid?: string;      // HEX UID карты или null
  error?: string;    // Ошибка PC/SC или null
}
```

#### Логика обработки в `nfcReaderStore`:

```javascript
const handleEvent = (payload) => {
  update(currentState => {
    if (payload.error) {
      return { 
        ...currentState, 
        status: 'error', 
        error: payload.error, 
        lastUid: null 
      };
    }
    
    return { 
      ...currentState, 
      status: 'ok', 
      error: null, 
      lastUid: payload.uid || null 
    };
  });
};
```

#### Сценарии статуса:

| Сценарий | UID | Error | Status | Описание |
|----------|-----|-------|--------|----------|
| Карта на ридере | HEX string | null | 'ok' | Карта обнаружена и прочитана |
| Р идер пуст | null | null | 'ok' | Р идер доступен, карты нет |
| Ошибка PC/SC | null | string | 'error' | Аппаратная ошибка ридера |
| Р идер не найден | null | "Считыватель не найден" | 'error' | Р идер отключен |

#### РРґРµРјРїРѕС‚РµРЅС‚РЅРѕСЃС‚СЊ:

Событие отправляется только при изменении payload. Сравнение происходит через JSON сериализацию:

```rust
if current_payload_json != last_payload_json {
    app_handle.emit("card-status-changed", payload.clone())?;
    last_payload_json = current_payload_json;
}
```

## 3. Классификация эндпоинтов API

### Публичные эндпоинты (для RPi)

| Endpoint | Method | Описание | РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ |
|----------|--------|----------|---------------|
| `/api/token` | POST | Аутентификация | Получение JWT токена |
| `/api/system/status` | GET | Статус экстренной остановки | Опрос RPi контроллерами |
| `/api/guests/{id}` | GET | Получение гостя по ID | RPi для проверки баланса |
| `/api/controllers/register` | POST | Р егистрация контроллера | Check-in RPi контроллеров |
| `/api/sync/pours` | POST | Синхронизация наливов | Отправка данных о наливах |

**Особенности:**
- Не требуют JWT аутентификации
- Оптимизированы для частого опроса
- Возвращают минимально необходимые данные
- **Требование заголовка `X-Internal-Token`** для эндпоинтов контроллеров (см. раздел 7)

### Эндпоинты требующие JWT (для Admin App)

#### Guests API
- `GET /api/guests/` - Список гостей
- `POST /api/guests/` - Создание гостя
- `PUT /api/guests/{id}` - Обновление гостя
- `POST /api/guests/{id}/cards` - Привязка карты
- `POST /api/guests/{id}/topup` - Пополнение баланса
- `GET /api/guests/{id}/history` - РСЃС‚РѕСЂРёСЏ операций

#### Kegs API
- `GET /api/kegs/` - Список кег
- `POST /api/kegs/` - Создание кеги
- `PUT /api/kegs/{id}` - Обновление кеги
- `DELETE /api/kegs/{id}` - Удаление кеги

#### Taps API
- `GET /api/taps/` - Список кранов
- `PUT /api/taps/{id}/keg` - Назначение кеги
- `DELETE /api/taps/{id}/keg` - Снятие кеги
- `PUT /api/taps/{id}` - Обновление крана

#### Beverages API
- `GET /api/beverages/` - Список напитков
- `POST /api/beverages/` - Создание напитка

#### System API
- `POST /api/system/emergency_stop` - Управление экстренной остановкой
- `GET /api/system/states/all` - Все флаги системы (debug)

#### Cards API
- `GET /api/cards/` - Список всех карт
- `POST /api/cards/` - Р егистрация карты
- `PUT /api/cards/{uid}/status` - РР·РјРµРЅРµРЅРёРµ статуса карты

#### Pours API
- `GET /api/pours/` - РСЃС‚РѕСЂРёСЏ наливов

## 4. Потоки данных

### Аутентификация:
```
UI в†’ sessionStore в†’ invoke('login') в†’ api_client::login() в†’ POST /api/token
                                            в†“
UI в†ђ sessionStore в†ђ JWT токен в†ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
```

### CRUD операции:
```
UI в†’ store в†’ invoke('command') в†’ api_client::function() в†’ HTTP endpoint
                                            в†“
UI в†ђ store в†ђ Обновленные данные в†ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
```

### NFC события:
```
Rust NFC thread в†’ card-status-changed в†’ nfcReaderStore в†’ UI
```

## 5. Обработка ошибок

### Rust в†’ Svelte:
```rust
#[derive(Debug, Serialize, Clone)]
pub struct AppError { 
    message: String,
}
```

### Svelte в†’ UI:
```javascript
try {
  await store.action();
} catch (error) {
  // error.message или error.toString()
}
```

### HTTP ошибки:
```rust
async fn handle_api_error(response: Response) -> String {
    if let Ok(error_body) = response.json::<ApiErrorDetail>().await {
        error_body.detail
    } else {
        format!("HTTP Error: {}", response.status())
    }
}
```

## 6. Конфигурация

### API Base URL:
```rust
const API_BASE_URL: &str = "http://localhost:8000/api";
```

### JWT токен:
```javascript
// Хранится в localStorage
localStorage.setItem('jwt_token', token);
```

### NFC опрос:
```rust
thread::sleep(Duration::from_millis(500));
```

## 7. Аутентификация контроллеров (X-Internal-Token)

### Требование для эндпоинтов контроллеров

Следующие публичные эндпоинты требуют заголовок `X-Internal-Token` для аутентификации RPi контроллеров:

- `POST /api/controllers/register` - Р егистрация контроллера
- `POST /api/sync/pours` - Синхронизация наливов

### Формат заголовка

```http
X-Internal-Token: <secret_token_string>
```

### Механизм проверки

1. **Серверная валидация:** Токен проверяется на соответствие предопределенному значению
2. **Безопасность:** Токен хранится в переменных окружения сервера
3. **Цель:** Предотвращение несанкционированного доступа к эндпоинтам контроллеров

### Пример запроса

```http
POST /api/sync/pours
Content-Type: application/json
X-Internal-Token: rpi_controller_secret_2024

{
  "pours": [
    {
      "client_tx_id": "tx_12345",
      "card_uid": "04AB7815CD6B80",
      "tap_id": 1,
      "start_ts": "2026-02-17T12:00:00Z",
      "end_ts": "2026-02-17T12:00:05Z",
      "volume_ml": 500,
      "price_cents": 350,
      "price_per_ml_at_pour": 0.0070
    }
  ]
}
```

### Переменные окружения

```bash
# На сервере backend
INTERNAL_CONTROLLER_TOKEN=rpi_controller_secret_2024
```

---

**Примечание:** Этот документ является источником правды для всех взаимодействий между компонентами системы. При изменении архитектуры необходимо обновлять данный контракт.

## M4 API Contract Addendum (2026-02-25)

### Updated sync payload
`POST /api/sync/pours` now requires `short_id` for every pour item:
- `client_tx_id` (string)
- `card_uid` (string)
- `tap_id` (int)
- `short_id` (string, 6-8)
- `start_ts` (datetime)
- `end_ts` (datetime)
- `volume_ml` (int)
- `price_cents` (int)

### New manual reconcile endpoint
`POST /api/visits/{visit_id}/reconcile-pour`
Payload:
- `tap_id` (int)
- `short_id` (string, 6-8)
- `volume_ml` (int)
- `amount` (decimal)
- `reason` (required string)
- `comment` (optional string)

Behavior:
- idempotent by `(visit_id, short_id)`;
- first successful call creates reconciled pour and unlocks visit;
- repeated call returns existing reconciled result.

### Audit actions used in M4
- `reconcile_done`
- `late_sync_matched`
- `late_sync_mismatch`
- `sync_conflict`

