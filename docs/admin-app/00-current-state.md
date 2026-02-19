# Admin App — Current State (Phase 0)

## 1) Где находится admin-app, стек и как запускать

- Путь: `admin-app/`.
- Формат: **Svelte SPA (Vite)** + **Tauri 2 (Rust bridge)**.
- Web runtime: `svelte-spa-router` (hash-based routes).
- Desktop runtime: Tauri команды (`invoke`) + события (`listen`) для NFC.

### Запуск (из текущего кода/доков)

```bash
cd admin-app
npm install
npm run dev        # web demo
npm run tauri dev  # desktop + Rust bridge + NFC events
```

### Высокоуровневая структура `admin-app`

> Ниже “рабочее” дерево без `node_modules/.svelte-kit`.

```text
admin-app/
├─ src/
│  ├─ App.svelte
│  ├─ main.js
│  ├─ routes/
│  │  ├─ Login.svelte
│  │  ├─ Dashboard.svelte
│  │  ├─ Guests.svelte
│  │  └─ TapsKegs.svelte
│  ├─ stores/
│  │  ├─ sessionStore.js
│  │  ├─ roleStore.js
│  │  ├─ guestStore.js
│  │  ├─ tapStore.js
│  │  ├─ kegStore.js
│  │  ├─ beverageStore.js
│  │  ├─ pourStore.js
│  │  ├─ systemStore.js
│  │  ├─ nfcReaderStore.js
│  │  ├─ uiStore.js
│  │  ├─ auditTrailStore.js
│  │  └─ demoGuideStore.js
│  ├─ components/
│  │  ├─ common/ (Modal)
│  │  ├─ feedback/ (ToastContainer, ConfirmDialog)
│  │  ├─ demo/ (DemoGuide)
│  │  ├─ guests/ (GuestList, GuestDetail, GuestForm, ...)
│  │  ├─ modals/ (NFCModal, TopUpModal, AssignKegModal)
│  │  ├─ taps/ (TapCard, TapGrid)
│  │  ├─ pours/ (PourFeed)
│  │  ├─ kegs/ (KegList, KegForm)
│  │  ├─ beverages/ (BeverageManager)
│  │  └─ system/ (NfcReaderStatus, ActivityTrail, InvestorValuePanel)
│  ├─ lib/
│  │  ├─ config.js
│  │  └─ api.js   # legacy/parallel auth wrapper
│  └─ styles/
│     └─ tokens.css
├─ src-tauri/
│  ├─ src/
│  │  ├─ main.rs
│  │  ├─ api_client.rs
│  │  ├─ nfc_handler.rs
│  │  └─ lib.rs
│  ├─ tauri.conf.json
│  └─ Cargo.toml
├─ package.json
└─ vite.config.js
```

---

## 2) Текущие экраны/роуты и назначение

## Router map (`src/App.svelte`)

- `#/` → `Dashboard.svelte`
- `#/guests` → `Guests.svelte`
- `#/taps-kegs` → `TapsKegs.svelte`
- fallback `*` → `Dashboard.svelte`
- При отсутствии `sessionStore.token`: показывается `Login.svelte` вместо shell.

## Экран: Login

- Аутентификация через:
  1. `invoke('login')` (Tauri путь),
  2. fallback на `POST /api/token` (web demo).
- При успехе сохраняет JWT в `localStorage` (`jwt_token`) через `sessionStore`.

## Экран: Dashboard

- Карточка статуса NFC reader (`NfcReaderStatus`).
- Сетка кранов (`TapGrid`).
- Лента наливов (`PourFeed`, polling 10s).
- Emergency Stop (подтверждение через modal, role-gated).
- Investor panel (role-gated) с агрегатами риска/состояния.

## Экран: Guests

- Поиск и список гостей.
- Создание/редактирование гостя (`GuestForm` в modal).
- Детальная карточка гостя (`GuestDetail`): баланс, статус, карты.
- Привязка карты через NFC (`NFCModal` + tauri event `card-status-changed`).
- Пополнение баланса (`TopUpModal`).

## Экран: Taps & Kegs

- Статус кранов (`TapGrid`), назначение кеги на кран (`AssignKegModal`).
- Инвентарь кег (`KegList`) + создание кеги (`KegForm`).
- Справочник напитков (`BeverageManager`).

---

## 3) API-интеграции (frontend ↔ tauri ↔ backend)

## Транспорт

- Основной путь: **Svelte stores** вызывают `@tauri-apps/api/core.invoke(...)`.
- Rust слой в `src-tauri/src/main.rs` пробрасывает команды в `api_client.rs`.
- `api_client.rs` ходит в backend по `http://localhost:8000/api`.
- Доп. web fallback для логина: прямой `fetch` в `Login.svelte`.

## Backend endpoints, реально используемые через `api_client.rs`

- Auth:
  - `POST /api/token`

- Guests / Cards / Top-up:
  - `GET /api/guests/`
  - `POST /api/guests/`
  - `PUT /api/guests/{guest_id}`
  - `POST /api/guests/{guest_id}/cards`
  - `POST /api/guests/{guest_id}/topup`

- Inventory / taps / pours:
  - `GET /api/kegs/`
  - `POST /api/kegs/`
  - `PATCH /api/kegs/{keg_id}`
  - `DELETE /api/kegs/{keg_id}`
  - `GET /api/taps/`
  - `PUT /api/taps/{tap_id}`
  - `POST /api/taps/{tap_id}/keg`
  - `DELETE /api/taps/{tap_id}/keg`
  - `GET /api/pours/?limit={n}`

- Beverage catalog:
  - `GET /api/beverages/`
  - `POST /api/beverages/`

- System:
  - `GET /api/system/status`
  - `PATCH /api/system/emergency_stop`

## Tauri команды, используемые UI

- Auth/CRUD: `login`, `get_guests`, `create_guest`, `update_guest`, `bind_card_to_guest`, `top_up_balance`, `get_kegs`, `create_keg`, `update_keg`, `delete_keg`, `get_taps`, `update_tap`, `assign_keg_to_tap`, `unassign_keg_from_tap`, `get_beverages`, `create_beverage`, `get_pours`, `get_system_status`, `set_emergency_stop`.
- NFC low-level: `list_readers`, `read_mifare_block`, `write_mifare_block`, `change_sector_keys`.
- NFC runtime events: `card-status-changed`.

---

## 4) Инвентаризация текущих user flows (as-is)

## 4.1 Логин сотрудника

- Ввод username/password → получить JWT → открыть shell.
- Нет явного `/me` запроса, user profile фактически отсутствует (в store `user: null`).

## 4.2 Регистрация гостя / редактирование

- `Guests` → `+ Новый гость` → форма → `create_guest`.
- Выбор гостя → `Редакт.` → форма → `update_guest`.

## 4.3 Выдача карты (привязка карты гостю)

- Выбрать гостя → `+ Привязать карту` (только если карт нет) → NFC modal.
- При событии UID → `bind_card_to_guest`.
- Повторная выдача/перевыпуск как отдельный flow в UI не оформлены.

## 4.4 Пополнение

- Выбрать гостя → `+ Пополнить` → numeric input суммы → `top_up_balance`.
- Payment method захардкожен в `cash`.

## 4.5 Проверка баланса / карты

- Баланс и список карт видны в `GuestDetail`.
- Истории транзакций по конкретному гостю на экране нет.

## 4.6 Блокировка/деактивация

- У гостя отображается `is_active`, но отдельного явного UX flow “заблокировать карту/гостя” на 1 клик нет.
- У кранов есть статусы, включая lock/maintenance (через tap management).

## 4.7 Смены

- Отдельного shift workflow (open shift / close shift / X/Z-like report) в текущем admin-app нет.

## 4.8 История/аудит

- Есть `ActivityTrail` — это **журнал UI-событий** (роль, demo guide), не финансовый аудит.
- Есть `PourFeed` (лента наливов), polling 10s, но это не полный audit trail транзакций кассира.

## 4.9 Статус устройств/связи

- Есть NFC статус-виджет (`initializing/ok/error`).
- Нет явного network status indicator (online/offline), нет unsynced queue indicator.

---

## 5) Ключевые ограничения из текущего кода

## Авторизация и сессия

- JWT хранится в `localStorage` (`jwt_token`), без refresh-механизма.
- Нет route-guard по ролям на уровне маршрутизатора; доступ чаще ограничен условным рендерингом секций.
- Роли сейчас скорее demo/UX-permission model (`roleStore`), не backend RBAC.

## Offline/degraded

- Реального offline-first нет: операции завязаны на API.
- Есть polling (`systemStore`, `pourStore`), но нет очереди синхронизации.
- NFC события могут идти локально, но бизнес-операции подтверждаются API.

## UI kit / стилизация

- Есть базовые токены в `src/styles/tokens.css` (цвета, spacing, radius, shadow).
- Но стили во многих компонентах локальные и не унифицированы (разные кнопки/отступы/цвета).
- Компонентная база уже есть (Modal, Toast, ConfirmDialog), но применяется не системно.

## Архитектурные ограничения

- Два параллельных подхода к API/авторизации:
  - `sessionStore` + `invoke` (основной путь),
  - `src/lib/api.js` (legacy fetch wrapper с другим token key `authToken`).
- В Tauri `api_client.rs` base URL захардкожен (`http://localhost:8000/api`), в web login используется `VITE_API_BASE_URL`.
  - Риск рассинхрона web/desktop окружений.

---

## 6) Наблюдаемые проблемы/долги (UI/UX/архитектура)

1. **Информационная архитектура “по сущностям”, не по операциям кассира**.
   - Сейчас навигация: Dashboard / Guests / Taps&Kegs.
   - Для POS-операций (выдать карту, пополнить, проверить) нет операционного “single-workspace” сценария.

2. **Нет shift-centric workflow**.
   - Отсутствуют opening/closing shift, выручка/инциденты, quick report.

3. **Недостаточная transaction safety для денежных операций**.
   - Нет undo window/операции отмены последнего действия.
   - Нет явного кассового журнала с финансовой трассировкой в интерфейсе.

4. **Неполная device/connectivity observability**.
   - Есть NFC status, но нет network/sync статусов и recovery подсказок.

5. **UI-consistency debt**.
   - Смешаны дизайн-токены и ad-hoc css; неодинаковая иерархия CTA, размер controls, плотность интерфейса.

6. **Role/security gap для B2B production**.
   - Role switch на фронте (demo-friendly), но без подтвержденной серверной модели пермишенов в UI-потоке.

7. **Нет фокусированного POS demo-path**.
   - Текущий интерфейс ближе к admin-console, чем к speed-first cashier workspace.

---

## 7) Итог Фазы 0 (готовность к следующему шагу)

- Базовая архитектура и интеграции уже достаточны для эволюции в demo-ready POS workspace без “перепила всего мира”.
- Критично в следующих фазах:
  1. Пересобрать IA вокруг **операций кассира**, а не сущностей.
  2. Ввести единые UX-стандарты для speed-first и error-proof flows.
  3. Закрыть demo-критичные gaps: shift flow, audit/incident UX, connectivity/status shell.
