# NFC Reconnect RCA And Options

## 1. Problem statement

`Admin App` теряет работоспособность NFC после сценария hot-unplug/hot-plug:

1. приложение запущено;
2. NFC reader физически отключают;
3. reader подключают обратно;
4. Windows снова видит устройство;
5. `Admin App` не возобновляет чтение карт;
6. восстановление происходит только после полного перезапуска `Admin App`.

Для барной эксплуатации это неприемлемо: NFC должен восстанавливаться без рестарта основного окна.

## 2. Current NFC architecture

### 2.1 Rust / Tauri side

- Точка входа с рабочей NFC-логикой: `admin-app/src-tauri/src/main.rs`, не шаблонный `src/lib.rs`.
- Низкоуровневые helper-функции: `admin-app/src-tauri/src/nfc_handler.rs`.
- При старте процесса создаётся один глобальный `pcsc::Context` через `Context::establish(Scope::User)` и кладётся в `AppState` как `Arc<Mutex<Context>>`.
- Этот же `Context` клонируется в отдельный background thread, запущенный в `.setup(...)`.
- Поток каждые 500 мс делает:
  - `list_readers_internal(&context)`
  - если список не пустой, берёт первый reader
  - `get_card_uid_internal(&context, reader_name)`
  - формирует `CardStatusPayload { uid, error }`
  - отправляет tauri event `card-status-changed`, только если payload изменился.

### 2.2 Reader / card lifecycle today

- Persistent object сейчас только один: `pcsc::Context`.
- Persistent `Card` handle не хранится.
- `Card` создаётся заново на каждом чтении UID в `get_card_uid_internal(...)` и дропается сразу после завершения вызова.
- Для MIFARE-команд (`read_mifare_block`, `write_mifare_block`, `change_sector_keys`) карта тоже подключается заново через `connect_and_authenticate(...)`.
- Освобождение `Context` явно не делается; он живёт до завершения процесса.

### 2.3 How reader presence is determined

- Reader presence определяется косвенно через `context.list_readers(...)`.
- Если readers list пуст, Rust трактует это как ошибку "reader unavailable".
- Если `list_readers(...)` падает по PC/SC ошибке, Rust тоже трактует это как ошибку "reader unavailable".
- UI не знает реальное имя активного reader: `nfcReaderStore` после успешной подписки просто подставляет display name `ACR122U`.

### 2.4 How card presence is determined

- Card presence определяется попыткой `context.connect(reader)` + APDU `FF CA 00 00 00` на получение UID.
- `pcsc::Error::NoSmartcard` и `pcsc::Error::RemovedCard` считаются нормальным состоянием "ридер есть, карты нет".
- Все остальные ошибки считаются аппаратной ошибкой reader/PCSC.

### 2.5 How UI receives NFC state

- Основной runtime канал: tauri event `card-status-changed`.
- `src/stores/nfcReaderStore.js` подписывается на событие один раз при инициализации модуля и обновляет глобальный UI status (`initializing` / `ok` / `error`).
- `src/components/modals/NFCModal.svelte` подписывается на то же событие локально в момент открытия modal:
  - `uid` -> `success` -> dispatch `uid-read`
  - `error` -> `error`
  - `uid = null, error = null` -> `waiting`
- Маршруты `Guests`, `Visits`, `LostCards` используют только `NFCModal`; прямого вызова `invoke('list_readers')` во frontend сейчас нет.

### 2.6 What is missing today

- Нет `ReaderManager` / state machine.
- Нет разделения состояний `disconnected` vs `error`.
- Нет explicit reconnect logic.
- Нет re-establish логики для `pcsc::Context`.
- Нет `SCardIsValidContext` / `Context::is_valid()` check.
- Нет `SCardGetStatusChange` / `Context::get_status_change()` мониторинга.
- Нет обработки `reader disappeared` / `reader reappeared` как отдельных событий.
- Нет backoff/retry policy.

## 3. Root cause analysis

### 3.1 Confirmed current failure mode

Практический отказ объясняется не stale UI reference и не long-lived card session:

- UI не хранит reader handle вообще.
- `Card` handle не живёт долго; он создаётся и дропается на каждом чтении.
- Polling thread не умирает, он продолжает крутиться бесконечно.

Следовательно, основная fault domain находится в persistent `pcsc::Context` и в отсутствии recovery logic вокруг него.

### 3.2 Real root cause

Root cause: `Admin App` держит один долгоживущий `pcsc::Context` на весь lifetime процесса и не умеет его валидировать, пересоздавать и повторно строить reader topology после hot-unplug/hot-plug.

На практике это выглядит так:

1. До unplug приложение работает, потому что каждый poll использует ещё валидный `Context`.
2. При unplug reader topology и/или PC/SC resource manager меняют состояние.
3. Дальнейшие вызовы `list_readers(...)` или `connect(...)` начинают возвращать PC/SC ошибки.
4. Текущий код переводит это только в `payload.error`, но не делает ни одного recovery action.
5. После replug loop продолжает использовать тот же старый `Context`.
6. Поскольку новый `Context` не создаётся, а reader state не отслеживается как state machine, приложение остаётся в деградированном состоянии до полного рестарта.
7. Рестарт помогает только потому, что при запуске заново выполняется `Context::establish(...)`.

### 3.3 Why this is credible technically

Локальный код уже показывает, что recovery невозможен:

- `Context` создаётся ровно один раз.
- В коде нет ни одного вызова `Context::establish(...)` после старта.
- В коде нет ни одного вызова `Context::is_valid()`.
- В коде нет классификации fatal PC/SC ошибок (`InvalidHandle`, `NoService`, `ServiceStopped`, `UnknownReader`, `ReaderUnavailable` и т.д.).

Внешняя модель PC/SC это подтверждает:

- `pcsc::Context::is_valid()` существует специально для проверки, что context ещё валиден.
- Microsoft `SCardIsValidContext` прямо указывает, что context может стать невалидным после остановки resource manager service.
- `pcsc` и WinSCard предоставляют `get_status_change` / `SCardGetStatusChange` и special reader `\\?PnP?\\Notification` именно для отслеживания insert/remove reader events.
- Текущий код ничего из этого не использует.

### 3.4 What the root cause is not

- Не `Tauri invoke` model: runtime NFC вообще идёт через push events, а не request/response.
- Не "старый reader name во frontend": frontend reader name сейчас даже не получает из Rust.
- Не persistent `Card` session: card handle не переживает poll iteration.
- Не отсутствие periodic rescan как такового: rescan номинально есть каждые 500 мс, но он завязан на старый `Context`, поэтому не является полноценным reconnect.

### 3.5 Most likely low-level error family after unplug

Без реального железа в этом расследовании нельзя зафиксировать конкретный код возврата, но по текущей реализации и PC/SC API наиболее вероятны ошибки из семейства:

- `InvalidHandle`
- `NoService`
- `ServiceStopped`
- `UnknownReader`
- `ReaderUnavailable`
- `NoReadersAvailable`

Критично то, что для всех этих состояний текущий код делает одно и то же: логирует ошибку и продолжает бесконечно использовать тот же `Context`.

## 4. State matrix

| App state | Reader state | Card state | Expected behavior | Actual behavior now | Gap |
| --- | --- | --- | --- | --- | --- |
| App started | Present | No card | Показать "reader ready", ждать карту | Работает: loop читает reader, `NoSmartcard`/`RemovedCard` трактуются как `uid=null,error=null` | Gap нет |
| App started | Present | Card present | Прочитать UID и передать в modal/store | Работает: UID уходит в `card-status-changed` | Gap нет |
| App started | Absent | No card | Показать "reader disconnected" и автоматически восстановиться, когда reader появится | Сейчас только generic error. Автовосстановление явно не реализовано и зависит от того, переживёт ли `Context` дальнейшие topology changes | Нет явного disconnected/reconnect lifecycle |
| App running | Reader disappears | No card | Перейти в `disconnected`, продолжать monitor/retry без рестарта | Переходит в generic error; recovery state не создаётся | Нет recovery path |
| App running after unplug | Reader reappears | No card | Переобнаружить reader, при необходимости пересоздать context, вернуться в `ready` | Практически не восстанавливается до перезапуска приложения | Нет context re-establish и topology rebuild |
| App running | Present | Card removed after previous read | Вернуться в waiting/ready | Работает через `NoSmartcard` / `RemovedCard` | Gap нет |

## 5. Solution options

### Option 1. Minimal in-process fix

#### How it works

- Оставить текущий polling model и текущий tauri event contract.
- Добавить слой recovery вокруг `pcsc::Context`:
  - проверять `Context::is_valid()` перед critical operations или после fatal error;
  - на fatal PC/SC errors сбрасывать старый `Context` и заново делать `Context::establish(Scope::User)`;
  - после re-establish повторно выполнять `list_readers(...)`;
  - если reader снова найден, loop продолжает работу без рестарта app.

#### What must change

- Заменить `Arc<Mutex<Context>>` на структуру, допускающую replacement (`Arc<Mutex<Option<Context>>>` или `Arc<Mutex<NfcRuntimeState>>`).
- Добавить helper `recreate_context_if_needed(...)`.
- В poller классифицировать ошибки на recoverable/no-card/fatal-context.
- Возможно, дать UI отдельный `disconnected` status вместо generic `error`.

#### Assessment

- Сложность реализации: низкая-средняя.
- Надёжность: средняя.
- Риск регрессий: низкий-средний, если сохранить существующий event contract.
- Для реального бара: лучше, чем сейчас, но всё ещё реактивная латка.
- Совместимость с текущей архитектурой: высокая.

#### Main drawback

- Это лечит только очевидный context reset path, но не строит полноценную модель reader lifecycle.
- Логика всё ещё остаётся "poll + пробуем connect", а не "monitor reader/card states".

### Option 2. ReaderManager внутри Admin App

#### How it works

- Вынести NFC runtime в отдельный in-process manager, владеющий state machine:
  - `starting`
  - `disconnected`
  - `scanning`
  - `ready`
  - `card_present`
  - `recovering`
  - `error`
- Manager держит context, reader states и reconnect policy.
- Для reader lifecycle использовать `Context::get_status_change(...)` + `PNP_NOTIFICATION` и bounded timeout.
- На fatal errors manager:
  - помечает state как `recovering`
  - валидирует/пересоздаёт context
  - rebuild reader states
  - возвращается в `ready` без участия UI.
- Снаружи сохранить совместимость:
  - продолжать эмитить `card-status-changed`
  - при желании добавить `nfc-reader-status-changed` с более богатым payload.

#### What must change

- Выделить новый Rust-layer, например `nfc_runtime.rs` / `reader_manager.rs`.
- Убрать raw loop из `main.rs`.
- Добавить state machine и таблицу переходов.
- Добавить typed classification PC/SC errors.
- Обновить UI только минимально:
  - различать `disconnected` и `error`
  - не менять существующие flows `Guests` / `Visits` / `LostCards`.

#### Assessment

- Сложность реализации: средняя.
- Надёжность: высокая.
- Риск регрессий: средний, но контролируемый.
- Для реального бара: хороший уровень эксплуатационной устойчивости.
- Совместимость с текущей архитектурой: высокая, потому что всё остаётся внутри текущего Tauri app.

#### Why this is the best near-term architecture

- Решает реальную проблему на правильном уровне: lifecycle железа.
- Не требует отдельного deployment unit.
- Не ломает backend, auth, runtime server config, localization и существующие UI flows.
- Делает поведение предсказуемым и наблюдаемым.

### Option 3. Separate NFC bridge / service / process

#### How it works

- Вынести NFC hardware integration в отдельный локальный процесс или Windows service.
- Сервис владеет PC/SC context, reader monitoring, reconnect, logs, retry policy.
- `Admin App` общается с ним по local IPC и получает только reader/card events.

#### What must change

- Новый deployment unit.
- IPC contract.
- Service lifecycle, install/update story, logging, watchdog.
- Изменения packaging/bundling для Tauri.
- Изменения в startup/shutdown и support procedures.

#### Assessment

- Сложность реализации: высокая.
- Надёжность: потенциально очень высокая, если сервис хорошо сделан.
- Риск регрессий: высокий на этапе внедрения.
- Для реального бара: хорошо только если нужно hard isolation или reuse reader across multiple apps.
- Совместимость с текущей архитектурой: средняя; это уже новое архитектурное направление.

#### Main drawback

- Это серьёзно повышает operational complexity раньше времени.
- Для текущего scope проекта это переусложнение, пока NFC используется только внутри одного `Admin App`.

## 6. Recommended solution

### Recommendation now

Рекомендую **Option 2: ReaderManager внутри `Admin App`**.

Это лучший баланс между:

- надёжностью;
- контролируемой сложностью;
- минимальным влиянием на остальной проект;
- соответствием текущей Tauri архитектуре.

Почему не Option 1:

- Option 1 технически может снять текущий pain point, но останется fragile recovery patch.
- Он не даёт нормальной модели `reader disappeared` / `reader reappeared`.
- Он оставляет UI и логику в зоне generic `error`, а не эксплуатационных состояний.

Почему не Option 3:

- Пока один desktop app является единственным потребителем reader, отдельный сервис не оправдан.
- Он нужен только если выяснится, что in-process layer на Windows остаётся нестабилен даже после нормального lifecycle manager.

## 7. Long-term recommendation

Если в будущем появится хотя бы один из факторов:

- несколько клиентов к одному reader;
- необходимость автономной диагностики и watchdog независимо от UI;
- требования к kiosk-grade resilience;
- общий hardware bridge для `Admin App` и других локальных компонентов,

тогда долгосрочно лучшим станет **Option 3: separate NFC bridge/service/process**.

Но на текущем этапе лучшая инженерная траектория:

1. Сначала внедрить Option 2 внутри `Admin App`.
2. Собрать реальные эксплуатационные логи по Windows hot-plug.
3. Только если этого окажется недостаточно, выносить NFC в отдельный процесс.

## 8. Risk analysis

### What must not break

- backend integration и runtime server URL;
- login/session flow;
- existing Tauri event bridge;
- текущее успешное чтение карт в normal path;
- сборка Tauri app;
- русифицированный UI.

### Main risks of change

- Ошибочная классификация PC/SC errors может перевести нормальное "карты нет" в ложный reconnect storm.
- Неправильный mutex/ownership design вокруг context может повесить MIFARE commands.
- Изменение payload contract `card-status-changed` может сломать `NFCModal` и `nfcReaderStore`.
- Добавление aggressive retries без backoff может создать noisy logs и лишнюю нагрузку на PC/SC stack.

### Risk mitigation

- Сохранить текущий `card-status-changed` contract backward-compatible.
- Разделить "reader disconnected" и "reader internal error".
- Ввести bounded retry/backoff.
- Изолировать manager в отдельный Rust module, не размазывая recovery logic по `main.rs`.
- Добавить ручной test matrix именно на Windows с реальным reader.

## 9. Implementation plan

Реализация в этом треке **не выполнялась**. Причина: для hot-plug recovery без физического reader рискованно сразу менять low-level lifecycle, не имея аппаратной проверки на целевом Windows workstation.

### Proposed implementation steps for Option 2

1. Создать Rust module `reader_manager` / `nfc_runtime`, который полностью владеет:
   - `pcsc::Context`
   - current reader set
   - current runtime state
   - reconnect/backoff policy
2. Перенести background thread из `main.rs` в этот manager.
3. Перейти с сырого 500 ms loop на `Context::get_status_change(...)` + `PNP_NOTIFICATION` с ограниченным timeout.
4. Явно классифицировать ошибки:
   - `NoSmartcard` / `RemovedCard` -> `ready`
   - `NoReadersAvailable` / `UnknownReader` / `ReaderUnavailable` -> `disconnected`
   - `InvalidHandle` / `NoService` / `ServiceStopped` -> `recovering` + recreate context
   - всё прочее -> `error`
5. После recreate context rebuild reader states и вернуться в `scanning/ready`.
6. Сохранить существующий `card-status-changed` payload для совместимости.
7. При необходимости добавить отдельное reader-status event, не ломая текущие modal flows.
8. Обновить `nfcReaderStore`, чтобы он различал `disconnected` и `error`.
9. Оставить `NFCModal` максимально неизменным: он должен по-прежнему получать `uid` и показывать понятную ошибку/ожидание.
10. После этого провести аппаратную ручную валидацию на Windows.

## 10. Verification plan

### Manual verification on Windows with real NFC reader

1. Запустить `Admin App` с подключённым reader.
2. Проверить baseline:
   - статус reader = ready
   - `NFCModal` читает UID
   - после снятия карты modal возвращается в waiting
3. Оставить app запущенным и физически отключить reader.
4. Убедиться, что UI переходит в `disconnected` или эквивалентное recoverable state, а не в permanent dead state.
5. Не перезапуская app, подключить reader обратно.
6. Убедиться, что в течение bounded recovery window статус снова становится `ready`.
7. Считать карту и убедиться, что UID снова приходит в `NFCModal`.
8. Повторить unplug/replug не менее 5 циклов подряд.
9. Повторить сценарий:
   - reader отсутствует на старте app
   - reader подключается позже
   - app должен войти в `ready` без рестарта
10. Повторить сценарий с открытым `NFCModal` во время unplug/replug.
11. Проверить, что backend-related flows не сломались:
   - bind card to guest
   - assign card to visit
   - lookup lost card by NFC

### Logging to capture during verification

- raw PC/SC error code/string;
- transitions state machine;
- timestamps of unplug / replug detection;
- context recreate attempts;
- successful return to `ready`.

## Evidence inspected

- Local code:
  - `admin-app/src-tauri/src/main.rs`
  - `admin-app/src-tauri/src/nfc_handler.rs`
  - `admin-app/src/stores/nfcReaderStore.js`
  - `admin-app/src/components/modals/NFCModal.svelte`
  - `admin-app/src/components/system/NfcReaderStatus.svelte`
  - `admin-app/src/components/system/SystemFallbackBanner.svelte`
  - `admin-app/src/App.svelte`
- External technical references:
  - Microsoft Learn: `SCardIsValidContext`
  - Microsoft Learn: `SCardGetStatusChange`
  - docs.rs `pcsc::Context`
  - docs.rs `pcsc::Error`
