# Russian Localization and RF Adaptation Audit

Date: 2026-03-10  
Branch: `audit/rus-localization-rf-adaptation`  
Scope: `admin-app`, `admin-app/src-tauri`, `rpi-controller`, operator-visible backend messages, primary docs/runbooks.

## 1. Executive summary

Проект находится в состоянии `mixed`.

- Основной operator UI уже в значительной степени русифицирован: страницы `Dashboard`, `Visits`, `Guests`, `LostCards`, `TapsKegs` и большинство модалок написаны по-русски.
- При этом в display layer всё ещё заметно протекают английские product labels, raw internal status codes, технические имена полей и денежные обозначения: `Beer Tap POS`, `POS Workspace`, `Role`, `Online/Offline`, `Demo mode`, `pending_sync`, `processing_sync`, `lock_set_at`, `reported_at`, `Guest ID`, `N/A`, `$`, `cents`.
- Внутренняя money model уже архитектурно закреплена на `*_cents`, `price_cents`, `amount_cents`, `balance_cents`, `price_per_ml_cents` в backend, controller, Rust DTO, payload'ах отчётов и POS stub seam.
- По единицам объёма проект уже близок к РФ-реалиям: рабочие runtime-пути почти полностью используют `ml/l`; признаков активного использования `oz/gallon/pint/lbs` в эксплуатационных путях не найдено.
- По датам и локали есть частичная адаптация (`ru-RU` используется в нескольких экранах), но многие operator-facing места всё ещё зависят от системного locale или показывают технические labels вместо нормального локального отображения.
- Документация split-состояния: operator docs частично русские, primary engineering docs в основном английские. Это допустимо, но нужен явный policy, что переводить, а что оставлять инженерным английским.

Общий риск миграции:

- `Low/Medium` для поэтапной локализации display layer, унификации formatters, operator messages и runbooks.
- `High` для переименования внутренних `*_cents` полей, API/DTO/DB schema, controller contract и POS seam.

Вывод: проект безопасно локализовать пофазно, если не трогать внутреннюю money model и не делать массовый rename доменных/API полей на этом этапе.

## 2. Audit by area

### 2.1 UI and operator-facing text

| Файл | Тип строки | Текущий текст | Проблема | Рекомендуемое действие |
| --- | --- | --- | --- | --- |
| `admin-app/index.html` | html locale / title | `lang="en"`, `Beer Tap Admin` | Входная точка приложения англоязычная | Перевести `lang` на `ru`, title на русское operator-friendly имя |
| `admin-app/src/App.svelte` | app shell title | `Beer Tap POS` | Англоязычный product title в основном shell | Заменить на локализованное имя рабочего места |
| `admin-app/src/App.svelte` | left rail action | `Guided demo mode` | Английская CTA в русском shell | Перевести на русский |
| `admin-app/src/routes/Dashboard.svelte` | diagnostic label | `API base URL` | Техническая англоязычная подпись видна оператору в diagnostic mode | Перевести label или пометить как dev-only |
| `admin-app/src/components/shell/ShellTopBar.svelte` | shell title | `POS Workspace` | Английский заголовок верхней панели | Перевести в display layer |
| `admin-app/src/components/shell/ShellTopBar.svelte` | accessibility label | `Role` | Английский `aria-label` | Заменить на `Роль` |
| `admin-app/src/components/shell/ShellStatusPills.svelte` | status pill | `Online / Offline` | Смешение русского и английского | Заменить на `В сети / Нет сети` |
| `admin-app/src/components/shell/ShellGuestContextChip.svelte` | guest status | `active / blocked` | Английские статусы в русском shell | Ввести русский mapping статусов |
| `admin-app/src/components/system/SystemFallbackBanner.svelte` | banner | `Demo mode` | Английский banner label | Перевести на `Демо-режим` |
| `admin-app/src/components/system/DemoModeToggle.svelte` | toggle | `Demo mode: ON/OFF` | Смешение языка | Перевести целиком |
| `admin-app/src/components/system/ServerSettingsModal.svelte` | field label | `Server URL` | Английская подпись в operator modal | Перевести на `Адрес сервера` |
| `admin-app/src/components/system/ServerSettingsModal.svelte` | source note | `runtime config (Tauri)` / `build/dev config` | Смешение русских и англоязычных терминов | Оставить англ. только в инженерной документации; в UI дать русский label |
| `admin-app/src/components/guests/GuestDetail.svelte` | fallback | `N/A` | Английский fallback | Заменить на `—` или `Нет данных` |
| `admin-app/src/components/guests/GuestDetail.svelte` | system labels | `Registered`, `Last Update`, `Guest ID` | Английские system labels | Перевести |
| `admin-app/src/components/guests/GuestDetail.svelte` | card status | `card.status` raw (`active`, `inactive`) | Raw enum уходит в UI | Ввести display mapping статусов карты |
| `admin-app/src/components/pours/PourFeed.svelte` | duration suffix | `30s` | Английская единица времени | Заменить на `30 с` |
| `admin-app/src/routes/Visits.svelte` | validation toast | `Fill short_id, volume, amount and reason` | Чисто английское operator message + internal names | Перевести и скрыть API naming |
| `admin-app/src/routes/Visits.svelte` | success/error toast | `Manual reconcile completed/failed` | Английские toast messages | Перевести |
| `admin-app/src/routes/Visits.svelte` | visit row state | `processing_sync (tap N)` | Raw internal status code в UI | Ввести display mapping статусов |
| `admin-app/src/routes/Visits.svelte` | details block | `lock_set_at`, `age: ~N min` | Техническое имя поля + `min` | Заменить на нормальные русские labels |
| `admin-app/src/routes/Visits.svelte` | form placeholders | `short_id`, `volume_ml`, `amount`, `reason`, `comment (optional)` | Оператору показываются внутренние имена payload | Заменить на русские labels/placeholders |
| `admin-app/src/routes/LostCards.svelte` | record fields | `reported_at`, `reason`, `comment`, `visit_id` | Raw backend field names | Скрыть технические names, оставить только display labels |
| `admin-app/src/components/modals/AssignKegModal.svelte` | selector text | `(... 50L) - ID: ...` | `L` и `ID` не согласованы с локалью UI | Нормализовать до `л` и русской подписи |

Дополнительные наблюдения:

- В `admin-app/src/components/taps/TapCard.svelte` статусы `active/locked/cleaning` уже частично маппятся на русский, что можно использовать как эталон для остальных экранов.
- В `admin-app/src/stores/shiftStore.js` уже есть локализация некоторых backend conflict-кодов (`active_visits_exist`, `pending_sync_pours_exist`), но это точечное решение, а не единая система отображения.

### 2.2 Money / currency

Категоризация:

- Категория 1: внутреннее хранение и доменная модель.
- Категория 2: отображение пользователю.
- Категория 3: архитектурно спорные места, где display и internal model сейчас пересекаются слишком тесно.

| Файл / слой | Поле или строка | Категория | Риск изменения | Рекомендация |
| --- | --- | --- | --- | --- |
| `backend/crud/pour_policy.py` | `balance_to_cents`, `price_per_ml_cents`, `required_cents_for_volume` | 1 | High | Не переименовывать; считать internal minor units |
| `backend/crud/visit_crud.py` | `balance_cents`, `price_per_ml_cents`, `allowed_overdraft_cents`, `required_cents` | 1 | High | Оставить как есть, менять только display layer |
| `backend/schemas.py` | `price_per_ml_cents`, `balance_cents`, `price_cents`, `total_amount_cents` | 1 | High | Не ломать API schema без отдельного ADR и версии API |
| `admin-app/src-tauri/src/api_client.rs` | `balance_cents`, `amount_cents`, `total_amount_cents` | 1 | High | Оставить naming в Rust DTO |
| `rpi-controller/sync_manager.py` | authorize/sync payload with `*_cents` | 1 | High | Не трогать controller/backend contract |
| `rpi-controller/database.py` | local SQLite column `price_cents` | 1 | High | Не переименовывать на фазе локализации |
| `backend/pos_adapter.py` | `amount_cents` | 1 | High | Сохранить как POS seam internal field |
| `backend/crud/card_crud.py` | `_guest_balance_cents`, `balance_cents` | 1 | High | Оставить как internal helper/API detail |
| `admin-app/src/components/reports/ShiftReportView.svelte` | `Сумма (коп)` + raw `total_amount_cents` / `amount_cents` | 2 | Low/Medium | Хранение оставить, в UI показывать `123,45 ₽` |
| `admin-app/src/routes/Dashboard.svelte` | `Сумма (коп)` + raw `total_amount_cents` | 2 | Low/Medium | Перевести на единый formatter рублей |
| `admin-app/src/components/kegs/KegList.svelte` | `${keg.purchase_price}` | 2 | Low | Убрать `$`, показывать рубли |
| `admin-app/src/components/kegs/KegForm.svelte` | `Цена покупки ($)`, default `100.00` | 2 | Low | Перевести знак валюты и realistic examples |
| `admin-app/src/components/beverages/BeverageManager.svelte` | `Цена за литр (напр., 7.50)` | 2 | Low | Сменить пример на рубли и поддержать русскую десятичную конвенцию |
| `admin-app/src/components/guests/GuestListItem.svelte` | `₽` + raw decimal | 2 | Low | Не собирать руками, вынести единый formatter |
| `admin-app/src/components/guests/GuestDetail.svelte` | raw `toFixed(2)` без валюты | 2 | Low | Добавить `₽` и `ru-RU` decimal formatting |
| `admin-app/src/components/pours/PourFeed.svelte` | `-amount_charged` без `₽` | 2 | Low | Показывать `-123,45 ₽` |
| `admin-app/src/routes/Visits.svelte` | `Баланс пополнен на ${event.detail.amount}` | 2 | Low | Форматировать сумму по-русски, а не raw decimal |
| `admin-app/src/components/modals/TopUpModal.svelte` | keypad и preview только с `.` и без `₽` | 2 | Medium | На UI/input уровне поддержать `,` и `.`; хранение не менять |
| `docs/sqlite_schema.sql` | `центах/копейках`, `рубли, доллары и т.д.` | 3 | Medium | Уточнить, что система использует копейки как minor units в текущей локализации |
| `backend/tests` и `rpi-controller/tests` | `cents`, test data in decimals | 3 | Medium | Не трогать на фазе 1; корректировать только вместе с display-layer изменениями |

Архитектурно спорные места:

- `*_cents` уже зацементированы в backend schema, Tauri bridge, controller queue, sync payload, shift reports и POS stub.
- Простая замена `cents -> kopeks` сейчас затронет DB schema, API contracts, Rust DTO, тесты, отчётные payload и будущий POS/r_keeper seam.
- На текущем этапе это не даёт бизнес-ценности, сопоставимой с риском. Практичный путь: оставить internal `_cents`, а везде в display layer показывать `₽/коп.`.

### 2.3 Units / measurement

| Место | Текущая единица | Подходит для РФ | Что менять |
| --- | --- | --- | --- |
| `backend`, `rpi-controller`, `admin-app` runtime | `ml`, `volume_ml`, `initial_volume_ml`, `current_volume_ml` | Да | Оставить как внутренний и display standard |
| `admin-app/src/components/kegs/KegList.svelte` | `мл` | Да | Оставить |
| `admin-app/src/components/system/InvestorValuePanel.svelte` | `л`, `мл` | Да | Использовать как ориентир для общего volume formatter |
| `admin-app/src/components/modals/AssignKegModal.svelte` | `L` | Частично | Для UI заменить на `л` |
| `rpi-controller/hardware.py`, `rpi-controller/test_hw.py` | `get_volume_liters()`, `Volume (L)` | Internal да / display спорно | Internal имя не трогать, debug/operator output локализовать при необходимости |
| repository-wide runtime search | `oz`, `gallon`, `pint`, `imperial`, `lbs` | Не найдено в рабочих путях | Массовая чистка imperial units не требуется |

Вывод по единицам:

- Главная проблема проекта не в американских единицах объёма, а в смешении money display и технических labels.
- Базовую volume model можно считать уже совместимой с РФ-реалиями.

### 2.4 Dates / time / locale formatting

| Место | Текущий формат | Рекомендация |
| --- | --- | --- |
| `admin-app/src/routes/Visits.svelte` | `toLocaleString('ru-RU')` | Хорошо; вынести в общий formatter |
| `admin-app/src/routes/LostCards.svelte` | `toLocaleString('ru-RU')` для части UI | Сохранить, но убрать raw field labels |
| `admin-app/src/components/kegs/KegList.svelte` | `toLocaleDateString('ru-RU')` | Хорошо; унифицировать |
| `admin-app/src/components/system/InvestorValuePanel.svelte` | `Intl.NumberFormat('ru-RU', { currency: 'RUB' })` | Эталон для money formatter |
| `admin-app/src/components/guests/GuestDetail.svelte` | `toLocaleString()` без locale | Сделать явный `ru-RU` |
| `admin-app/src/routes/Dashboard.svelte` | `toLocaleString()` без locale | Сделать явный `ru-RU` |
| `admin-app/src/components/reports/ShiftReportView.svelte` | `toLocaleString()` без locale | Сделать явный `ru-RU` |
| `admin-app/src/components/pours/PourFeed.svelte` | `toLocaleTimeString([], ...)` без locale | Сделать явный `ru-RU` formatter времени |
| `admin-app/src/components/system/ActivityTrail.svelte` | `toLocaleTimeString([], ...)` без locale | То же |
| `admin-app/src/routes/Visits.svelte` | `lock_set_at`, `age: ~N min` | Помимо locale убрать технические labels |
| `admin-app/src/routes/LostCards.svelte` | `reported_at: {toLocaleString()}` | Нормализовать label и locale |
| `admin-app/src/stores/auditTrailStore.js` | `toISOString()` | Оставить как внутренний timestamp storage |
| `admin-app/src/routes/LostCards.svelte` | `toISOString()` для query params | Оставить как transport/API format |

Вывод по датам:

- Проблема не в отсутствии date API, а в отсутствии единого display formatter и в неполной локализации labels вокруг дат.
- Для operator UI достаточно Phase 1 унификации на `ru-RU` без изменения transport-форматов.

### 2.5 Documentation

| Документ | Оставить / перевести / частично адаптировать | Комментарий |
| --- | --- | --- |
| `README.md` | Частично адаптировать | Primary entry point полностью на английском; нужен русский summary или bilingual intro, dev commands можно оставить |
| `docs/INDEX.md` | Частично адаптировать | Это вход в документацию; нужен русский summary и policy по языкам |
| `docs/API_REFERENCE.md` | Частично адаптировать | Технический контракт можно оставить на английском, но нужен русский glossary и пояснение про `*_cents` |
| `docs/architecture/*` | Оставить на английском + частично адаптировать | Frozen architecture docs разумно оставить инженерными; добавить glossary/terminology note |
| `docs/dev/*` | Оставить на английском | Это инженерные runbooks, не operator docs |
| `docs/reports/*` | В основном оставить как архив | Массово переводить исторические отчёты нецелесообразно |
| `docs/SOP_Bartender.md` | Обязательно адаптировать | Это operator doc; сейчас русскоязычный, но содержит не-РФ реалии (`21+`) |
| `docs/sqlite_schema.sql` | Частично адаптировать | Уточнить терминологию денег и убрать двусмысленное `рубли, доллары и т.д.` |
| `docs/openapi_fragment.yaml` | Частично адаптировать | URL/examples можно оставить техническими, но monetary descriptions стоит привести к рублям/копейкам |
| `docs/INTERFACE_CONTRACT.md` | Частично адаптировать | Engineering doc можно оставить англоязычным, но добавить note про minor units и operator-facing mappings |

Дополнительные documentation findings:

- `docs/SOP_Bartender.md` использует `21+`, тогда как для РФ нужно `18+`.
- `README.md`, `docs/API_REFERENCE.md`, `docs/dev/ADMIN_APP_BACKEND_URL.md`, часть архитектурных документов содержат `localhost` и `cybeer-hub`. Для инженерных runbooks это нормально, но такие примеры должны быть явно помечены как dev-only.
- В primary docs активно используются `pending_sync`, `top-up`, `refund`, `FIFO`, `POS-ready stub seam`. Для инженерной документации это допустимо, но нужен единый glossary, чтобы operator docs и инженерные docs не расходились по терминологии.

## 3. Recommended migration strategy

### Phase 1 — Display layer only

- Ввести единые helpers/formatters:
  - `formatMoneyRub(amountDecimal)`
  - `formatMinorUnitsRub(cents)`
  - `formatVolumeRu(ml)`
  - `formatDateTimeRu(ts)`
  - `formatTimeRu(ts)`
- Русифицировать остатки operator-facing текстов в `admin-app`:
  - shell,
  - settings,
  - visit/lost-card details,
  - shift reports,
  - demo/fallback/status labels.
- Убрать из UI raw internal labels:
  - `pending_sync`,
  - `processing_sync`,
  - `lock_set_at`,
  - `reported_at`,
  - `visit_id`,
  - `short_id`,
  - `volume_ml`.
- Локализовать controller terminal/operator messages:
  - `Pouring`,
  - `Session finished`,
  - `est. cost`,
  - `cents`,
  - `Top up balance`.
- Не менять DB/API/model names.

### Phase 2 — Documentation and terminology cleanup

- Сформировать glossary терминов:
  - визит,
  - смена,
  - налив,
  - кега,
  - пополнение,
  - возврат,
  - потерянная карта,
  - ручная сверка,
  - ожидает синхронизации.
- Привести operator docs к РФ-реалиям:
  - `18+` вместо `21+`,
  - рубли/копейки,
  - русские labels и operational wording.
- Обновить primary docs:
  - `README.md`,
  - `docs/INDEX.md`,
  - `docs/API_REFERENCE.md`.
- Зафиксировать policy:
  - runtime/operator UI на русском;
  - engineering docs допустимо на английском;
  - исторические отчёты и deep architecture docs не переводятся массово.
- Явно описать в документации, что `*_cents` означает internal minor units, а пользователь видит `₽/коп.`.

### Phase 3 — Deep domain/API rename (только если будет обосновано)

- Выполнять только после отдельного ADR.
- Сначала оценить, есть ли вообще бизнес-смысл переименовывать:
  - DB columns,
  - Pydantic schemas,
  - Rust DTO,
  - controller payload,
  - POS stub payload.
- Если менять, делать только через compatibility strategy:
  - alias fields,
  - API versioning,
  - staged deprecation,
  - миграционные скрипты,
  - обновление контрактов controller/backend одновременно.
- Вероятный практичный исход: Phase 3 может оказаться не нужна.

## 4. Hard recommendations

- Оставить internal money fields в `*_cents`, `price_cents`, `balance_cents`, `amount_cents`; менять только display layer.
- Не переименовывать сейчас DB/API поля. Это слишком рискованно и не даёт быстрой пользовательской ценности.
- Сделать единый money formatter и использовать его везде, где оператор видит сумму.
- Сделать единый locale/display formatter для даты, времени и объёма.
- Перестать пробрасывать raw backend/Tauri errors напрямую в UI; ввести translation/display mapping для operator-facing ошибок.
- Поддержать в денежных вводах русскую десятичную конвенцию на UI-уровне: ввод с `,` должен быть допустим, даже если внутренне всё нормализуется в точку.
- Оставить `ml/l` как базовые единицы и не трогать внутренние `get_volume_liters()` и similar names без отдельной причины.
- Ввести glossary терминов и status mapping, чтобы `pending_sync`, `processing_sync`, `active`, `blocked` не протекали в operator UI.
- В первую очередь адаптировать operator docs под РФ:
  - возраст `18+`,
  - рубли/копейки,
  - русские labels,
  - понятные operational instructions.
- Не трогать POS/r_keeper integration на этом этапе; текущая архитектура ей не противоречит.

## 5. Final verdict

`SAFE TO START RUSSIAN LOCALIZATION IN PHASED MODE`

Почему:

- display layer уже частично русифицирован и хорошо отделим от внутренней модели;
- money/domain naming действительно зацементирован, но его можно безопасно не трогать;
- явных архитектурных blockers для перевода UI, operator messages, отчётов и runbooks не найдено;
- основная работа следующего этапа — это унификация formatters, cleanup operator-facing strings и согласование терминологии, а не подготовительный deep refactor.
