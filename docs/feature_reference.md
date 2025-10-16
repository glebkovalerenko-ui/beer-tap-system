# Feature Reference — Admin / Bartender App
**Beer Tap System — v1.0 (Phase 1 deliverables)**

**Purpose:** полный список фич для приложения бармена/администраторa, приоритеты, критерии приёма и прямое соответствие API (paths).  
Source of truth: `project_context.md` (beer-tap-system) + `project_context.md` (nfc-prototype).

---

## Summary: High-level priorities
- **High:** Quick Guest Lookup, Assign Card, Top-up Balance, Pour Status & Sync View, Emergency Stop, Keg/Tap Management, Multi-controller support (basic registration)
- **Medium:** Guest transaction history, Keg CRUD, Reports (pours), Inventory alerts
- **Low:** Mobile mode, advanced automation, remote valve control (deferred / needs hardware)

---

## Table of features (detailed)

| # | Category | Feature | Priority | Acceptance criteria (concrete) | API mapping (endpoint) |
|---:|---|---|---:|---|---|
| 1 | Guests | Quick Guest Lookup (name / phone / uid) | High | Search returns results <1s on local network; supports partial matches; returns guest id, name, balance, assigned cards. | `GET /api/guests?q=<term>` |
| 2 | Guests | Create / Edit Guest (UI form) | High | Create returns 201 with guest object; edit returns 200; validation for required fields. | `POST /api/guests/`, `PUT /api/guests/{guest_id}` |
| 3 | Guests | Assign / Unassign RFID card to guest | High | When Assign invoked: UI prompts "tap card", backend binds `uid` -> guest; success 200. Unassign sets card inactive. | `POST /api/cards/bind`, `POST /api/cards/unbind` |
| 4 | Guests | Top-up Balance (manual) | High | UI form sends amount+method; server records transaction and returns new balance; change reflected in guest listing. | `POST /api/guests/{guest_id}/topup` |
| 5 | Pours | Pour Status View (pending / confirmed / failed) | High | Dashboard shows pour list with status; pending highlighted; confirmations update within poll interval or websocket. | `GET /api/pours?status=pending` |
| 6 | Safety | Emergency Stop / Lockdown | High | Clicking Emergency sends command to backend; backend sets flag and controllers poll and stop pours immediately; audit log entry. | `POST /api/system/emergency` |
| 7 | Kegs/Taps | Keg CRUD | High | Create, Update, Delete keg; GET list returns inventory data; DB persist. | `POST /api/kegs`, `GET /api/kegs`, `PUT /api/kegs/{keg_id}`, `DELETE /api/kegs/{keg_id}` |
| 8 | Kegs/Taps | Assign Keg to Tap | High | UI selects keg and assigns to tap; tap state shows assigned keg. | `PUT /api/taps/{tap_id}/assign-keg` |
| 9 | Controllers | Controller Registration & Health | High | Controller can register with backend (controller_id, firmware, last_seen); backend shows controller list with heartbeat. | `POST /api/controllers/register`, `GET /api/controllers` |
|10 | Guests | Guest Transaction History | Medium | Guest page shows list of pours and top-ups; filter by date; CSV export. | `GET /api/guests/{guest_id}/transactions` |
|11 | Reports | Shift / Day pour report | Medium | Generate report for period; export CSV; includes totals and per-tap breakdown. | `GET /api/reports/pours?from=&to=` |
|12 | Ops | Open/Close Shift | Low | Shift open/close recorded; reports tied to shifts. | `POST /api/shifts/open`, `POST /api/shifts/close` |

---

## UI/UX patterns & small components (implementation notes)

- **Guest card component**: name, balance, assigned card(s) UIDs, quick actions: Top-up, Assign Card, View history.
- **Search bar**: global, debounce 250ms, returns guests/taps/kegs.
- **Pour list**: columns [time, guest, tap, volume, price, status(client_tx_id)], status color-coded.
- **Emergency control**: prominent red button in header; confirmation modal with reason input; logged in audit.

---

## Acceptance criteria (global)

- All **High** priority features must be implemented, tested and deployed to staging before enabling pilot.
- All endpoints must return standard HTTP codes and JSON body with `{ "success": true/false, "data": ..., "error": { code, message } }` pattern.
- All admin actions must create an audit log entry: `{ actor_user_id, action, target_id, timestamp, details }`.

---

## API mapping (per feature) — quick reference

> Note: This section is a concise map. Full OpenAPI fragment follows as separate file (`openapi_fragment.yaml`).

### Guests
- `GET /api/guests?q=<term>&limit=20&page=1` — search/list guests. Response: list of Guest.
- `POST /api/guests` — create guest. Body: `{ name, phone?, notes? }`.
- `GET /api/guests/{guest_id}` — guest detail.
- `PUT /api/guests/{guest_id}` — update guest.
- `POST /api/guests/{guest_id}/topup` — top-up balance. Body: `{ amount, method, note }`.
- `GET /api/guests/{guest_id}/transactions?from=&to=` — transaction history.

### Cards
- `POST /api/cards/bind` — bind card to guest. Body: `{ guest_id, uid }` (uid can be null to indicate "wait for tap" mode).
- `POST /api/cards/unbind` — unbind card. Body: `{ uid }` or `{ card_id }`.
- `GET /api/cards?guest_id=` — list cards by guest.

### Pours / Sync
- `POST /api/sync/pours` — existing sync endpoint for controllers (batch). Body: `{ pours: [ { client_tx_id, controller_id, tap_id, guest_card_uid, volume_ml, price, timestamp } ] }`
- `GET /api/pours?status=pending|confirmed|failed&limit=50` — view pours.

### System / Emergency
- `POST /api/system/emergency` — sets emergency flag. Body: `{ reason, actor_user_id }`
- `GET /api/system/status` — returns global flags (emergency, maintenance).

### Kegs & Taps
- `POST /api/kegs` — create keg. Body: `{ name, volume_ml, remaining_ml, cost_price, sell_price }`
- `GET /api/kegs` — list kegs.
- `PUT /api/kegs/{keg_id}` — update keg.
- `DELETE /api/kegs/{keg_id}` — remove keg.
- `PUT /api/taps/{tap_id}/assign-keg` — Body: `{ keg_id }`
- `GET /api/taps` — list taps (status, assigned_keg, last_pour)

### Controllers
- `POST /api/controllers/register` — Controller registers itself. Body: `{ controller_id, firmware_version, ip, capabilities }`
- `GET /api/controllers` — Admin list with last_seen, backlog_count.

---

## Implementation notes for devs

- Use `react-query` for data fetching / cache invalidation. Hook the search bar to cancel previous requests.
- For long-polling pour status updates, prefer WebSocket if available; otherwise poll `/api/pours?status=pending`.
- All critical actions (top-up, assign card, emergency stop) must be idempotent or generate unique action IDs to avoid duplication.
- Add audit log middleware in backend: wrap state-changing endpoints to create audit entries.

---

## QA scenarios (short list — for E2E)

1. **Guest create & assign card**: Create guest → open Assign modal → tap card (simulate) → backend binds → guest card visible.
2. **Top-up & pour flow**: Top-up guest balance → simulate pour on controller to consume amount → confirm pour synced and balance decreased.
3. **Emergency stop**: Trigger Emergency → controller receives flag on next poll and refuses pours → UI shows emergency status.
4. **Keg assign**: Create keg → assign to tap → tap shows assigned keg; pour records include keg_id.

---

## Next steps
- Use `openapi_fragment.yaml` as contract basis for frontend scaffolding.
- Create GitHub issues from `features-to-issues.csv`.
- Implement RBAC & authentication as prerequisite before pilot.

---


---

### **Feature Reference & Implementation Summary (Phases 2.0 & 2.1)**

**Документ по состоянию на:** 12 октября 2025 г.
**Цель:** Предоставить исчерпывающее, основанное на фактах описание реализованного функционала и принятых архитектурных решений в рамках Фаз 2.0 и 2.1. Документ является "источником правды" для команды и ИИ-ассистентов.

---

### **I. Реализованные руководящие принципы (Guiding Principles)**

Следующие архитектурные принципы были успешно внедрены и являются стандартом для всего реализованного кода:

1.  **Принцип разделения сущностей (Реализовано):**
    *   **Сущности:** `Beverage` (справочник) и `Keg` (экземпляр).
    *   **Механизм:** Связь установлена через `ForeignKey("beverages.beverage_id")`.
    *   **Расположение:** `backend/models.py`.

2.  **Принцип конечных автоматов (Реализовано):**
    *   **Сущности:** `Keg` и `Tap` имеют явное поле `status` с четко определенными состояниями.
    *   **Механизм:** `Column(String, nullable=False, default=...)`.
    *   **Расположение:** `backend/models.py`.

3.  **Принцип транзакционной целостности (Частично реализовано):**
    *   **Сущности:** Модели `Pour` и `Transaction` созданы.
    *   **Механизм:** Модели определены в `backend/models.py`. Активная логика по созданию финансовых транзакций (`top-up`) будет реализована в Фазе 2.2.

4.  **Принцип идемпотентности (Реализовано):**
    *   **Сущности:** Бизнес-процесс назначения кеги на кран.
    *   **Механизм:** В CRUD-функции `assign_keg_to_tap` добавлена явная проверка `if db_tap.keg_id == keg_id: return db_tap`.
    *   **Расположение:** `backend/crud/tap_crud.py`.

5.  **Принцип "жадной загрузки" (Eager Loading) (Реализовано):**
    *   **Сущности:** `Keg` (со связанным `Beverage`) и `Tap` (со связанными `Keg` и `Beverage`).
    *   **Механизм:** Во всех `SELECT` запросах в CRUD-модулях используется `options(joinedload(...))` для загрузки связанных данных одним запросом.
    *   **Расположение:** `backend/crud/keg_crud.py`, `backend/crud/tap_crud.py`.
    *   **Вывод:** Это стандарт для проекта, предотвращающий ошибки `DetachedInstanceError` и оптимизирующий производительность.

---

### **II. Фаза 2.0: Фундамент — Модели и Схемы (ЗАВЕРШЕНО)**

**Результат:** Заложена полная, синхронизированная и версионируемая основа данных для всей будущей бизнес-логики.

*   **Задача 2.0.1: Создание и миграция моделей данных (SQLAlchemy)**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Артефакты:**
        *   Файл `backend/models.py` содержит полные и актуальные классы SQLAlchemy для всех сущностей (`Beverage`, `Keg`, `Tap`, `Card`, `Transaction`, `AuditLog`), включая связи `relationship`.
        *   Внедрен инструмент миграций **Alembic**. В директории `backend/alembic/versions` находятся сгенерированные скрипты миграций, которые привели схему БД в актуальное состояние.

*   **Задача 2.0.2: Создание схем данных (Pydantic)**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Артефакты:**
        *   Файл `backend/schemas.py` содержит полные и **полностью синхронизированные** с `models.py` Pydantic-схемы. Все расхождения (имена полей, типы ID, лишние/недостающие поля) были устранены.
        *   Для всех сущностей определены схемы `...Base`, `...Create`, `...Update` (где применимо) и основная схема для чтения, использующая `from_attributes = True`.

*   **Задача 2.0.3: Инициализация CRUD-модулей**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Артефакты:**
        *   Создана модульная структура в директории `backend/crud/`.
        *   Создан файл `backend/crud/__init__.py` для упрощения импортов.
        *   Все необходимые файлы (`beverage_crud.py`, `keg_crud.py`, `tap_crud.py` и др.) созданы и содержали заглушки, которые были реализованы в Фазе 2.1.

---

### **III. Фаза 2.1: Управление инвентарём (Inventory Management) (ЗАВЕРШЕНО)**

**Результат:** Реализован полный, защищенный и протестированный API для управления инвентарными единицами бара.

*   **Задача 2.1.1: CRUD для `Beverage` (Справочник напитков)**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Реализация:**
        *   **Логика:** `backend/crud/beverage_crud.py`. Содержит проверку на уникальность имени.
        *   **API:** `backend/api/beverages.py`. Реализованы эндпоинты `POST /`, `GET /`, `GET /{beverage_id}`.
    *   **API-контракт (`schemas.BeverageCreate`):**
        *   `name` (str, обязательное): Название напитка.
        *   `brewery` (str, опциональное): Пивоварня.
        *   `style` (str, опциональное): Стиль (e.g., "Lager").
        *   `abv` (Decimal, опциональное): Крепость.
        *   `sell_price_per_liter` (Decimal, обязательное): Розничная цена.

*   **Задача 2.1.2: CRUD для `Keg` (Управление кегами)**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Реализация:**
        *   **Логика:** `backend/crud/keg_crud.py`. Содержит логику проверки существования `beverage_id`, автоматической установки `current_volume_ml`, обновления временных меток (`tapped_at`, `finished_at`) и запрета на удаление используемой кеги.
        *   **API:** `backend/api/kegs.py`. Реализованы эндпоинты `POST /`, `GET /`, `GET /{keg_id}`, `PUT /{keg_id}`, `DELETE /{keg_id}`.
    *   **API-контракт (`schemas.KegCreate`):**
        *   `beverage_id` (uuid.UUID, обязательное): ID напитка из справочника.
        *   `initial_volume_ml` (int, обязательное): Начальный объем.
        *   `purchase_price` (Decimal, обязательное): Закупочная стоимость.
    *   **Статусы (`status`):**
        *   `full` (по умолчанию): Новая, полная кега.
        *   `in_use`: Кега подключена к крану.
        *   `empty`: Кега закончилась.

*   **Задача 2.1.3: CRUD для `Tap` (Управление кранами)**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Реализация:**
        *   **Логика:** `backend/crud/tap_crud.py`. Содержит проверку на уникальность `display_name` и запрет на удаление крана с подключенной кегой.
        *   **API:** `backend/api/taps.py`. Реализованы эндпоинты `POST /`, `GET /`, `GET /{tap_id}`, `PUT /{tap_id}`, `DELETE /{tap_id}`.
    *   **API-контракт (`schemas.TapCreate`):**
        *   `display_name` (str, обязательное): Имя крана для отображения в UI.
    *   **Статусы (`status`):**
        *   `locked` (по умолчанию): Кран заблокирован и неактивен.
        *   `active`: Кран готов к наливу, к нему подключена кега.
        *   `cleaning`: Кран находится в режиме очистки.
        *   `empty`: Кран активен, но подключенная кега пуста.

*   **Задача 2.1.4: Реализация ключевого бизнес-процесса "Назначение кеги на кран"**
    *   **Статус:** **ЗАВЕРШЕНО.**
    *   **Реализация:**
        *   **Логика:** `backend/crud/tap_crud.py`. Функции `assign_keg_to_tap` и `unassign_keg_from_tap` содержат всю логику проверок (идемпотентность, статусы крана и кеги) и атомарного изменения состояний.
        *   **API:** `backend/api/taps.py`.
    *   **API-контракт:**
        *   **`PUT /api/taps/{tap_id}/keg`**: Назначает кегу. Принимает `schemas.TapAssignKeg` (`keg_id: uuid.UUID`).
            *   **Эффект:** Статус крана -> `active`. Статус кеги -> `in_use`.
        *   **`DELETE /api/taps/{tap_id}/keg`**: Снимает кегу.
            *   **Эффект:** Статус крана -> `locked`. Статус кеги -> `full` (если не была пустой).

---

### **Ключевые выводы и состояние проекта**

Проект успешно прошел две важнейшие фазы, в ходе которых был заложен надежный и масштабируемый фундамент данных и реализован основной инвентарный контур. Все новые модули следуют единым архитектурным принципам, защищены аутентификацией и документированы через OpenAPI. 


---

### **Feature Reference & Implementation Summary (Phases 2.2 & 2.3)**

**Документ по состоянию на:** 13 октября 2025 г.
**Цель:** Предоставить исчерпывающее, основанное на фактах описание реализованного функционала и принятых архитектурных решений в рамках Фаз 2.2 и 2.3. Документ является "источником правды" для команды и ИИ-ассистентов.

---

### **I. Подтверждение следования руководящим принципам**

В ходе реализации Фаз 2.2 и 2.3 были последовательно применены все утвержденные архитектурные принципы:

1.  **Принцип разделения сущностей:** Успешно применен для связки `Guest` (клиент) и `Card` (его идентификатор).
2.  **Принцип конечных автоматов:** Реализован для сущности `Card`, которая теперь имеет собственный жизненный цикл, определяемый полем `status`.
3.  **Принцип транзакционной целостности:** Является ядром реализованной функции пополнения баланса. Каждое пополнение — это неизменяемая запись в `Transaction`, на основе которой обновляется кэшированный баланс гостя.
4.  **Принцип идемпотентности:** Реализован в логике привязки карты к гостю, предотвращая ошибки при повторных запросах.

---

### **II. Фаза 2.2: Управление гостями и финансами (ЗАВЕРШЕНО)**

**Результат:** Бэкенд получил полнофункциональное ядро для управления гостями, их идентификаторами (картами) и финансовым балансом. Система готова к проведению клиентских операций.

#### **Задача 2.2.1: Управление RFID-картами (`Card`) (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **`backend/crud/card_crud.py`**: Реализованы функции для полного жизненного цикла карт: создание с проверкой на уникальность `card_uid`, чтение списка и одной карты, обновление статуса.
    *   **`backend/crud/guest_crud.py`**: Реализованы бизнес-процессы `assign_card_to_guest` и `unassign_card_from_guest`. Логика содержит все необходимые проверки (существование сущностей, статусы, проверка на занятость) и атомарно обновляет связи и статусы.
*   **API:**
    *   **`backend/api/cards.py`**: Управляет картами как самостоятельными сущностями.
        *   `POST /api/cards`: Регистрирует новую карту в системе.
        *   `GET /api/cards`: Возвращает список всех карт.
        *   `PUT /api/cards/{card_uid}/status`: Обновляет статус карты.
    *   **`backend/api/guests.py`**: Управляет картами в контексте гостя.
        *   `POST /api/guests/{guest_id}/cards`: Привязывает карту к гостю.
        *   `DELETE /api/guests/{guest_id}/cards/{card_uid}`: Отвязывает карту от гостя.

*   **Схемы (API-контракты):**
    *   **`schemas.CardCreate`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Тело запроса для `POST /api/cards`.
        *   **Параметры:**
            *   `card_uid` (str, обязательное): Уникальный идентификатор, считанный с физической карты.
    *   **`schemas.Card`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Схема для ответа API, представляющая одну карту.
        *   **Параметры:**
            *   `card_uid` (str): Уникальный идентификатор.
            *   `guest_id` (UUID, опциональное): ID гостя, к которому привязана карта.
            *   `status` (str): Текущий статус карты.
            *   `created_at` (datetime): Время регистрации карты в системе.
        *   **Статусы (`status`):**
            *   `inactive` (по умолчанию): Карта зарегистрирована, но не привязана к гостю или была отвязана.
            *   `active`: Карта привязана к гостю и готова к использованию.
            *   `lost`: Карта помечена как утерянная и заблокирована для использования.
    *   **`schemas.CardAssign`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Тело запроса для `POST /api/guests/{guest_id}/cards`.
        *   **Параметры:**
            *   `card_uid` (str, обязательное): UID карты, которую нужно привязать.
    *   **`schemas.CardStatusUpdate`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Тело запроса для `PUT /api/cards/{card_uid}/status`.
        *   **Параметры:**
            *   `status` (str, обязательное): Новый статус для карты (e.g., "lost").

---

#### **Задача 2.2.2: Реализация пополнения баланса (`Transaction`) (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **`backend/crud/transaction_crud.py`**: Реализована ключевая функция `create_topup_transaction`. Она **атомарно** (в рамках одной транзакции БД) выполняет две операции: создает запись в таблице `transactions` и обновляет поле `balance` в таблице `guests`.
*   **API:**
    *   **`backend/api/guests.py`**: Добавлен новый эндпоинт `POST /api/guests/{guest_id}/topup`.
*   **Схемы (API-контракты):**
    *   **`schemas.TopUpRequest`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Тело запроса для пополнения баланса.
        *   **Параметры:**
            *   `amount` (Decimal, обязательное): Сумма пополнения. Валидируется на > 0.
            *   `payment_method` (str, обязательное): Метод оплаты (e.g., "cash", "card").

---

#### **Задача 2.2.3: Получение истории операций гостя (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **`backend/crud/guest_crud.py`**: Реализована функция `get_guest_history`. Она выполняет агрегацию данных из двух разных таблиц (`transactions` и `pours`), преобразует их в унифицированный формат `HistoryItem` и сортирует в хронологическом порядке. Используется "жадная загрузка" для оптимизации запросов.
*   **API:**
    *   **`backend/api/guests.py`**: Добавлен новый эндпоинт `GET /api/guests/{guest_id}/history` с опциональными параметрами `start_date` и `end_date` для фильтрации.
*   **Схемы (API-контракты):**
    *   **`schemas.HistoryItem`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Представляет одну унифицированную запись в истории операций.
        *   **Параметры:**
            *   `timestamp` (datetime): Время операции.
            *   `type` (str): Тип операции (`top-up`, `pour`, `refund` и т.д.).
            *   `amount` (Decimal): Сумма операции. **Положительная** для пополнений, **отрицательная** для списаний (наливов).
            *   `details` (str): Человекочитаемое описание операции (e.g., "Пополнение: Наличные" или "Налив: Guinness 500 мл").
    *   **`schemas.GuestHistoryResponse`**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Корневой объект ответа для эндпоинта истории.
        *   **Параметры:**
            *   `guest_id` (UUID): ID гостя, чья история запрашивалась.
            *   `history` (List[HistoryItem]): Отсортированный список всех операций.

---

### **III. Фаза 2.3: Доработка логики наливов (Pour Processing) (ЗАВЕРШЕНО)**

**Результат:** Эндпоинт синхронизации с контроллерами (`/api/sync/pours/`) превращен в интеллектуальный процессинговый центр, который обеспечивает целостность всех данных в системе при каждом наливе.

#### **Задачи 2.3.1 & 2.3.2: Обогащение данных и Атомарное обновление состояния (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **`backend/crud/pour_crud.py`**: Создана новая основная функция `process_pour`, которая инкапсулирует всю бизнес-логику обработки одного налива.
    *   **Процесс валидации:** Перед обработкой функция выполняет исчерпывающий набор проверок:
        1.  Существование и полная конфигурация всех связанных сущностей (`Card`, `Guest`, `Tap`, `Keg`, `Beverage`).
        2.  Проверка статусов: `Guest.is_active`, `Card.status == "active"`, `Tap.status == "active"`, `Keg.status == "in_use"`.
        3.  Расчет стоимости на стороне сервера на основе `Beverage.sell_price_per_liter`.
        4.  Проверка достаточности баланса гостя (`Guest.balance`).
        5.  Проверка достаточности остатка в кеге (`Keg.current_volume_ml`).
    *   **Процесс обновления (выполняется атомарно):**
        1.  Создается новая запись в таблице `pours`.
        2.  Уменьшается `Guest.balance`.
        3.  Уменьшается `Keg.current_volume_ml`.
        4.  Если кега закончилась, ее статус меняется на `empty`, и статус связанного крана также меняется на `empty`.
*   **API:**
    *   **`backend/main.py`**: Эндпоинт `POST /api/sync/pours/` был полностью переработан.
    *   **Новая логика:** Он итерирует по пачке наливов, для каждого вызывает `pour_crud.process_pour` и управляет транзакцией для всей пачки. Если хотя бы один налив в пачке не проходит валидацию, он помечается как `rejected`, но остальные продолжают обрабатываться. Если происходит ошибка на этапе `db.commit()`, вся транзакция откатывается, гарантируя, что ни один налив из пачки не будет сохранен частично.
*   **Схемы (API-контракты):**
    *   **`schemas.SyncRequest` (вход)**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Тело запроса от контроллера, содержащее список наливов.
        *   **Ключевые параметры в `PourData`:** `client_tx_id`, `card_uid`, `tap_id`, `volume_ml`.
    *   **`schemas.SyncResponse` (выход)**
        *   **Расположение:** `backend/schemas.py`
        *   **Назначение:** Ответ сервера на запрос синхронизации.
        *   **Ключевые параметры в `SyncResult`:**
            *   `client_tx_id` (str): Идентификатор, позволяющий контроллеру сопоставить ответ с запросом.
            *   `status` (str): Статус обработки (`accepted` или `rejected`).
            *   `reason` (str, опциональное): **Теперь содержит детальную причину** в случае дубликата или отказа (e.g., "duplicate", "Insufficient funds", "Tap is not active").


---

### **Feature Reference & Implementation Summary (Phase 2.4)**

**Документ по состоянию на:** 13 октября 2025 г.
**Цель:** Предоставить исчерпывающее, основанное на фактах описание реализованного функционала и принятых архитектурных решений в рамках Фазы 2.4. Документ является "источником правды" для команды и ИИ-ассистентов.

---

### **I. Подтверждение следования руководящим принципам**

В ходе реализации Фазы 2.4 были последовательно применены все утвержденные архитектурные принципы:

1.  **Принцип конечных автоматов:** Успешно применен для управления глобальным состоянием системы (флаг `emergency_stop_enabled`), позволяя переводить всю систему между состояниями `Normal` и `Emergency`.
2.  **Принцип транзакционной целостности:** Является ядром реализованной системы аудита. Каждое административное действие порождает неизменяемую запись в `AuditLog`, создавая полный "бумажный след" всех важных изменений в системе.

---

### **II. Фаза 2.4: Системные и операционные функции (ЗАВЕРШЕНО)**

**Результат:** Бэкенд получил три критически важных системных модуля, которые превращают его из простого API для бизнес-операций в полноценную, управляемую и прозрачную платформу. Система теперь "знает" о своем оборудовании, может управляться на глобальном уровне и автоматически документирует все важные изменения.

---

#### **Задача 2.4.1: Реализация полного цикла управления контроллерами (RPi) (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **Расположение:** `backend/crud/controller_crud.py`.
    *   **Реализация:** Реализована ключевая функция `register_controller`, которая работает по принципу **"upsert"** (создать, если не существует; обновить, если существует). При каждом вызове она находит контроллер по `controller_id` и либо создает новую запись, либо обновляет `ip_address`, `firmware_version` и (автоматически через `onupdate`) `last_seen`.

*   **API:**
    *   **Расположение:** `backend/api/controllers.py`.
    *   **Эндпоинты:**
        *   **`POST /api/controllers/register`**: **Открытый** эндпоинт, предназначенный для вызова с RPi-контроллеров. Служит для их первоначальной регистрации и последующих периодических "check-in".
        *   **`GET /api/controllers/`**: **Защищенный** эндпоинт, требующий аутентификации. Предназначен для использования в Admin App для отображения списка всего зарегистрированного оборудования и его статуса.

*   **Схемы (API-контракты):**
    *   **`schemas.ControllerRegister`**
        *   **Расположение:** `backend/schemas.py`.
        *   **Назначение:** Тело запроса для `POST /api/controllers/register`.
        *   **Параметры:**
            *   `controller_id` (str, обязательное): Уникальный идентификатор контроллера (например, MAC-адрес).
            *   `ip_address` (str, обязательное): Текущий IP-адрес контроллера в локальной сети.
            *   `firmware_version` (str, опциональное): Версия прошивки, запущенной на контроллере.
    *   **`schemas.Controller`**
        *   **Расположение:** `backend/schemas.py`.
        *   **Назначение:** Схема для ответа API, представляющая один зарегистрированный контроллер.
        *   **Параметры:**
            *   `controller_id` (str): Уникальный идентификатор.
            *   `ip_address` (str): Последний известный IP-адрес.
            *   `firmware_version` (str, опциональное): Последняя известная версия прошивки.
            *   `created_at` (datetime): Время первой регистрации контроллера.
            *   `last_seen` (datetime): Время последнего "check-in" от контроллера.

---

#### **Задача 2.4.2: Реализация системы экстренной остановки (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **Расположение:** `backend/crud/system_crud.py`.
    *   **Реализация:** Реализована гибкая key-value система для управления глобальными флагами. Ключевая функция `get_state` автоматически создает флаг со значением по умолчанию (`"false"`), если он еще не существует в БД. Функция `set_state` работает по принципу "upsert".

*   **API:**
    *   **Расположение:** `backend/api/system.py`.
    *   **Эндпоинты:**
        *   **`GET /api/system/state`**: **Открытый** эндпоинт, который опрашивается контроллерами. Возвращает список всех глобальных флагов системы, гарантированно включая `emergency_stop_enabled`.
        *   **`PUT /api/system/state/emergency_stop`**: **Защищенный** эндпоинт для администраторов. Позволяет включать или выключать режим экстренной остановки.

*   **Схемы (API-контракты):**
    *   **`schemas.SystemStateItem`**
        *   **Расположение:** `backend/schemas.py`.
        *   **Назначение:** Представляет один унифицированный флаг в ответе `GET /api/system/state`.
        *   **Параметры:**
            *   `key` (str): Имя флага (e.g., "emergency_stop_enabled").
            *   `value` (str): Значение флага (e.g., "true", "false").
    *   **`schemas.SystemStateUpdate`**
        *   **Расположение:** `backend/schemas.py`.
        *   **Назначение:** Тело запроса для `PUT /api/system/state/emergency_stop`.
        *   **Параметры:**
            *   `value` (str, обязательное): Новое значение для флага. Принимает только `"true"` или `"false"`.

---

#### **Задача 2.4.3: Автоматическое аудирование действий (ЗАВЕРШЕНО)**

*   **Логика:**
    *   **Механизм:** Реализован как **FastAPI Middleware**.
    *   **Расположение:** `backend/main.py`.
    *   **Принцип работы:** Middleware автоматически перехватывает **все успешные** HTTP-запросы с методами `POST`, `PUT`, `DELETE`. После выполнения эндпоинта оно извлекает из запроса и ответа всю необходимую информацию (ID пользователя из JWT, тип действия, ID целевого объекта) и вызывает CRUD-функцию для создания записи в журнале.
    *   **Вспомогательная логика:**
        *   **Расположение:** `backend/crud/audit_crud.py`.
        *   **Реализация:** Функция `create_audit_log` принимает все данные от Middleware и создает запись в таблице `AuditLog`.

*   **API (для чтения логов):**
    *   **Расположение:** `backend/api/audit.py`.
    *   **Эндпоинты:**
        *   **`GET /api/audit/`**: **Защищенный** эндпоинт для администраторов, который возвращает список последних записей из журнала аудита в обратном хронологическом порядке.

*   **Схемы (API-контракты):**
    *   **`schemas.AuditLog`**
        *   **Расположение:** `backend/schemas.py`.
        *   **Назначение:** Схема для ответа API, представляющая одну запись в журнале аудита.
        *   **Параметры:**
            *   `log_id` (uuid.UUID): Уникальный ID записи лога.
            *   `actor_id` (str, опциональное): ID пользователя, совершившего действие (например, "admin").
            *   `action` (str): Тип действия, формируется как `METHOD_URL_PATH` (e.g., "POST_/api/beverages/").
            *   `target_entity` (str, опциональное): Зарезервировано для будущего использования.
            *   `target_id` (str, опциональное): ID сущности, над которой было совершено действие (автоматически извлекается из ответа API).
            *   `details` (str, опциональное): Зарезервировано для будущего использования (например, для сохранения тела запроса).
            *   `timestamp` (datetime): Точное время совершения действия.


---

### **Feature Reference & Implementation Summary (Phase 2.5, Tasks 2.5.1 & 2.5.2)**

**Документ по состоянию на:** 13 октября 2025 г.
**Цель:** Предоставить исчерпывающее, основанное на фактах описание реализованных решений по безопасности и документированию API. Документ является "источником правды" для команды и ИИ-ассистентов, продолжающих работу над проектом.

---

### **Фаза 2.5: Финализация и безопасность (ЧАСТИЧНО ЗАВЕРШЕНО)**

#### **Задача 2.5.1: Комплексная ревизия безопасности эндпоинтов (ЗАВЕРШЕНО)**

*   **Статус:** **ЗАВЕРШЕНО.**
*   **Описание проделанной работы:** Был проведен полный аудит всех файлов в директории `backend/api/`. Каждый эндпоинт был проверен на соответствие требованиям безопасности.
*   **Результаты аудита и принятые архитектурные решения:**
    1.  **Принцип глобальной защиты роутеров:** Для всех роутеров, где **каждый** эндпоинт требует аутентификации, защита реализована на уровне всего роутера с помощью `dependencies=[Depends(security.get_current_user)]`.
        *   **Затронутые модули:** `beverages`, `kegs`, `taps`, `guests`, `cards`, `audit`.
        *   **Вывод:** Это является **стандартом проекта** для полностью защищенных модулей.
    2.  **Принцип локальной защиты эндпоинтов:** Для роутеров, содержащих как публичные, так и защищенные эндпоинты, защита реализована на уровне конкретной функции с помощью зависимости `current_user: Annotated[schemas.Guest, Depends(security.get_current_user)]`.
        *   **Затронутые модули:** `controllers`, `system`.
    3.  **Подтвержденный список публичных эндпоинтов:** Следующие эндпоинты намеренно оставлены без аутентификации для взаимодействия с оборудованием или для входа в систему:
        *   `POST /api/token` (в `main.py`)
        *   `POST /api/sync/pours/` (в `main.py`)
        *   `POST /api/controllers/register` (в `api/controllers.py`)
        *   `GET /api/system/state` (в `api/system.py`)

---

#### **Задача 2.5.2: Актуализация и верификация API-документации (ЗАВЕРШЕНО)**

*   **Статус:** **ЗАВЕРШЕНО.**
*   **Описание проделанной работы:** Была проведена полная ревизия и полировка автоматически генерируемой документации Swagger UI (`/docs`). Все файлы в `backend/api/` были обновлены в соответствии с "Золотым стандартом" документирования, принятым для проекта.
*   **"Золотой стандарт" документирования (Принято как стандарт проекта):**
    1.  **Краткий заголовок (`summary`):** Каждый эндпоинт в декораторе `@router` имеет параметр `summary`, содержащий короткую, интуитивно понятную фразу, описывающую его действие (e.g., "Создать нового гостя").
    2.  **Развернутое описание (Docstring):** Сразу после сигнатуры функции идет многострочный `docstring`, который подробно описывает:
        *   Основное назначение эндпоинта.
        *   Ключевую **бизнес-логику** и выполняемые проверки.
        *   **Побочные эффекты** (например, изменение статусов связанных сущностей).
    3.  **Коды ответа:** Для операций создания (`POST`) явно указан `status_code=201` или `status.HTTP_201_CREATED`. Для операций удаления (`DELETE`) используется `status_code=204`.

---

### **Справочник ключевых API-эндпоинтов (по состоянию на 13.10.2025)**

#### **Группа `System`**
*   `GET /api/system/state`
    *   **summary:** "Получить глобальное состояние системы"
    *   **description:** Возвращает все глобальные флаги состояния системы. Используется контроллерами для опроса.
    *   **security:** **Публичный**
*   `PUT /api/system/state/emergency_stop`
    *   **summary:** "Включить/выключить экстренную остановку"
    *   **description:** Изменяет флаг `emergency_stop_enabled`. Доступно только для администраторов.
    *   **security:** **Защищено аутентификацией**

#### **Группа `Controllers`**
*   `POST /api/controllers/register`
    *   **summary:** "Зарегистрировать контроллер (check-in)"
    *   **description:** Эндпоинт для регистрации или обновления данных RPi-контроллера. Реализует логику "upsert".
    *   **security:** **Публичный**
*   `GET /api/controllers/`
    *   **summary:** "Получить список контроллеров"
    *   **description:** Возвращает список всех зарегистрированных контроллеров. Доступно только для администраторов.
    *   **security:** **Защищено аутентификацией**

#### **Группа `Audit`**
*   `GET /api/audit/`
    *   **summary:** "Получить журнал аудита"
    *   **description:** Возвращает последние записи из журнала аудита в обратном хронологическом порядке.
    *   **security:** **Защищено аутентификацией**

---

### **Справочник ключевых схем данных (Pydantic)**

#### **Схема `schemas.KegCreate`**
*   **Расположение:** `backend/schemas.py`
*   **Назначение:** Тело запроса для `POST /api/kegs/`. Используется для регистрации новой кеги.
*   **Параметры:**
    *   `beverage_id` (uuid.UUID): ID напитка из справочника `Beverage`.
    *   `initial_volume_ml` (int): Начальный объем кеги в миллилитрах.
    *   `purchase_price` (Decimal): Закупочная стоимость всей кеги.

#### **Схема `schemas.TapAssignKeg`**
*   **Расположение:** `backend/schemas.py`
*   **Назначение:** Тело запроса для `PUT /api/taps/{tap_id}/keg`. Используется для назначения кеги на кран.
*   **Параметры:**
    *   `keg_id` (uuid.UUID): ID кеги, которую нужно назначить.

#### **Схема `schemas.TopUpRequest`**
*   **Расположение:** `backend/schemas.py`
*   **Назначение:** Тело запроса для `POST /api/guests/{guest_id}/topup`. Используется для пополнения баланса гостя.
*   **Параметры:**
    *   `amount` (Decimal): Сумма пополнения (должна быть > 0).
    *   `payment_method` (str): Метод оплаты (e.g., "cash", "card").

#### **Схема `schemas.ControllerRegister`**
*   **Расположение:** `backend/schemas.py`
*   **Назначение:** Тело запроса для `POST /api/controllers/register`. Используется RPi-контроллером для "check-in".
*   **Параметры:**
    *   `controller_id` (str): Уникальный ID контроллера (e.g., MAC-адрес).
    *   `ip_address` (str): Текущий IP-адрес.
    *   `firmware_version` (str, опционально): Версия прошивки.

#### **Жизненные циклы (Статусы)**

*   **Сущность:** `Keg`
    *   **Расположение:** `backend/models.py`
    *   **Статусы:**
        *   `full`: Новая, полная кега, готова к использованию.
        *   `in_use`: Кега подключена к крану и используется для наливов.
        *   `empty`: Кега закончилась.
*   **Сущность:** `Tap`
    *   **Расположение:** `backend/models.py`
    *   **Статусы:**
        *   `locked`: Кран свободен и заблокирован (безопасное состояние по умолчанию).
        *   `active`: Кран готов к наливу, к нему подключена кега.
        *   `cleaning`: Кран находится в режиме очистки.
        *   `empty`: Кран активен, но подключенная кега пуста.
*   **Сущность:** `Card`
    *   **Расположение:** `backend/models.py`
    *   **Статусы:**
        *   `inactive`: Карта зарегистрирована, но не привязана к гостю.
        *   `active`: Карта привязана к гостю и готова к использованию.
        *   `lost`: Карта помечена как утерянная и заблокирована.


---

### **Feature Reference & Implementation Summary (Task 2.5.3: Integration Testing)**

**Документ по состоянию на:** 14 октября 2025 г.
**Цель:** Предоставить исчерпывающее, основанное на фактах описание реализованной тестовой системы, ее архитектуры, а также ключевых модернизаций, выполненных в основном коде для обеспечения тестируемости. Документ является "источником правды" для команды и ИИ-ассистентов.

---

### **I. Руководящие принципы реализованной тестовой системы**

В рамках Задачи 2.5.3 была спроектирована и внедрена система интеграционного тестирования, основанная на следующих незыблемых принципах:

1.  **Принцип "Локальная разработка — прежде всего" (Local-First Development):**
    *   **Решение:** Тесты запускаются локально (`pytest`) с использованием сверхбыстрой базы данных **SQLite в оперативной памяти**.
    *   **Обоснование:** Это обеспечивает практически **мгновенную обратную связь** для разработчика (цикл "код -> тест -> исправление" занимает доли секунды), что кардинально повышает продуктивность по сравнению с запуском тестов в Docker-контейнерах на этапе локальной разработки.

2.  **Принцип абсолютной изоляции (Absolute Isolation):**
    *   **Механизм:** Файл `backend/tests/conftest.py` с помощью фикстуры `client` гарантирует, что **для каждой отдельной тестовой функции** создается своя собственная, абсолютно чистая база данных, которая уничтожается сразу после завершения теста.
    *   **Результат:** Тесты не влияют друг на друга и на рабочую базу данных. Их можно запускать в любом порядке, и результат всегда будет предсказуемым.

3.  **Принцип независимости и отделимости (Independence & Separability):**
    *   **Механизм:** Весь тестовый код находится в отдельной директории `backend/tests/`. Все зависимости, необходимые только для тестов, декларируются в отдельном файле `backend/requirements-test.txt`.
    *   **Результат:** Тестовая система не "загрязняет" основной код приложения. Ее можно легко модифицировать, расширять или даже полностью удалить (просто стерев папку `tests` и файл `requirements-test.txt`) без малейшего вреда для production-кода.

4.  **Принцип фокуса на бизнес-процессах (Business Process Focus):**
    *   **Механизм:** Основное внимание уделено сквозным тестам ("lifecycles"), которые имитируют реальные сценарии работы пользователя, проверяя всю цепочку взаимодействия API-эндпоинтов.
    *   **Результат:** Тесты проверяют не просто отдельные функции, а **корректность работы системы как единого целого**.

---

### **II. Архитектура и реализация тестовой системы**

#### **Файл `backend/requirements-test.txt`**
*   **Назначение:** Определяет Python-зависимости, необходимые исключительно для запуска тестов.
*   **Ключевая практика:** Содержит строку `-r requirements.txt`, которая гарантирует, что при установке тестовых зависимостей будут также установлены все зависимости основного приложения. Это решает проблему `ModuleNotFoundError` для библиотек вроде `jose` или `fastapi`.

#### **Файл `backend/pytest.ini`**
*   **Назначение:** Конфигурационный файл для `pytest`.
*   **Ключевая практика:** Содержит директиву `pythonpath = .`.
    *   **Проблема, которую решает:** `ModuleNotFoundError: No module named 'main'`.
    *   **Механизм:** Указывает `pytest` считать корневую директорию `backend/` источником модулей, что позволяет тестам из `backend/tests/` корректно импортировать код приложения (например, `from main import app`).

#### **Файл `backend/tests/conftest.py` — Сердце тестовой системы**
*   **Назначение:** Содержит общие настройки и фикстуры, доступные для всех тестов.
*   **Реализованная логика:**
    1.  **Тестовая БД:** Создается `engine` для **SQLite в оперативной памяти**.
    2.  **Подмена зависимости:** Функция `override_get_db` создана для предоставления сессий к тестовой БД. Ключевая строка `app.dependency_overrides[get_db] = override_get_db` "на лету" подменяет стандартную зависимость `get_db` на ее тестовый аналог во всем приложении FastAPI.
    3.  **Фикстура `client`:** Это основная фикстура, используемая в тестах. С `scope="function"` она выполняет следующий цикл для **каждого теста**:
        *   **Перед тестом:** `Base.metadata.create_all(bind=engine)` создает все таблицы в чистой БД.
        *   **Во время теста:** Предоставляет `TestClient(app)` для выполнения "виртуальных" HTTP-запросов.
        *   **После теста:** `Base.metadata.drop_all(bind=engine)` полностью уничтожает все таблицы.

#### **Верифицированные тестовые сценарии**

*   **Файл `backend/tests/test_security.py`**
    *   **Назначение:** Простой "дымовой тест", который подтверждает, что система безопасности работает, а тестовая среда настроена корректно.
    *   **Сценарий:** Выполняет запрос к защищенному эндпоинту `GET /api/kegs/` без токена аутентификации и проверяет, что получает ожидаемую ошибку `401 Unauthorized`.

*   **Файл `backend/tests/test_business_lifecycles.py`**
    *   **Назначение:** Проверяет ключевые сквозные бизнес-процессы.
    *   **Сценарий 1: `test_keg_and_tap_lifecycle`**
        *   **Верифицируемые сущности:** `Beverage`, `Keg`, `Tap`.
        *   **Верифицируемые схемы:** `schemas.BeverageCreate`, `schemas.KegCreate`, `schemas.TapCreate`, `schemas.TapAssignKeg`.
        *   **Процесс:** Аутентификация -> Создание Напитка -> Создание Кеги -> Создание Крана -> **Назначение Кеги на Кран** -> Проверка статусов (`active`, `in_use`) -> **Снятие Кеги с Крана** -> Проверка статусов (`locked`, `full`).
    *   **Сценарий 2: `test_guest_and_finance_lifecycle`**
        *   **Верифицируемые сущности:** `Guest`, `Card`, `Transaction`.
        *   **Верифицируемые схемы:** `schemas.GuestCreate`, `schemas.CardCreate`, `schemas.CardAssign`, `schemas.TopUpRequest`.
        *   **Процесс:** Аутентификация -> Создание Гостя (со всеми обязательными полями) -> Регистрация Карты -> **Привязка Карты к Гостю** -> **Пополнение баланса** -> Финальная проверка баланса гостя в БД.

---

### **III. Ключевые модернизации кода, выполненные для обеспечения тестируемости**

Внедрение тестов выявило ряд архитектурных проблем в основном коде. Их исправление сделало приложение более надежным, гибким и соответствующим лучшим практикам.

#### **1. Модернизация `backend/models.py`**
*   **Проблема:** Использование PostgreSQL-специфичной функции `uuid_generate_v4()` на уровне БД (`server_default`). Это приводило к падению тестов на SQLite.
*   **Решение:** Генерация UUID была перенесена со стороны СУБД на сторону приложения.
*   **Изменение:** Все `server_default=text("uuid_generate_v4()")` были заменены на `default=uuid.uuid4`. Также `PG_UUID` был заменен на универсальный `UUID` из `sqlalchemy`.
*   **Результат:** Модели стали **база-агностическими**, что позволило использовать SQLite в тестах и гарантировало их прохождение.

#### **2. Модернизация `backend/main.py`**
*   **Проблема:** Код `models.Base.metadata.create_all(bind=engine)` находился в `lifespan` или глобальной области видимости. Это приводило к попытке подключения к PostgreSQL в момент импорта файла, что ломало тесты.
*   **Решение:** Ответственность за создание схемы БД была полностью убрана из кода приложения.
*   **Изменение:** Строка `create_all` была удалена из `main.py`.
*   **Результат:** Приложение стало "чистым" — его импорт не производит никаких побочных эффектов (side-effects), таких как подключение к БД. Создание схемы теперь является обязанностью инструментов миграции (Alembic) в production и тестовых фикстур в `conftest.py`.

#### **3. Модернизация `backend/database.py` и `backend/schemas.py`**
*   **Проблема:** Код использовал устаревший синтаксис SQLAlchemy и Pydantic, что приводило к многочисленным `DeprecationWarning` в логах тестов.
*   **Решение:** Был проведен рефакторинг для соответствия современным версиям библиотек.
*   **Изменения:**
    *   В `database.py`: `declarative_base` теперь импортируется из `sqlalchemy.orm`.
    *   В `schemas.py`: `class Config` заменен на `model_config = ConfigDict(...)`; `orm_mode = True` заменен на `from_attributes=True`; `example="..."` в `Field` заменен на `json_schema_extra={'example': ...}`.
*   **Результат:** Код стал современным, чистым, и все предупреждения были устранены. Это повышает долгосрочную поддерживаемость проекта.

---

### **IV. Как запустить тесты**

Для запуска всего тестового набора необходимо выполнить следующие команды из корневой директории `backend/`:
```bash
# 1. Установить все необходимые зависимости (основные + тестовые)
pip install -r requirements-test.txt

# 2. Запустить pytest
pytest
```
**Ожидаемый результат:** `3 passed`.