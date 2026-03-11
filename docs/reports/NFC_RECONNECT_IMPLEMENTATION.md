# NFC Reconnect Implementation

## 1. Problem recap

`Admin App` терял работоспособность NFC после hot unplug/replug, потому что при старте создавался один долгоживущий `pcsc::Context`, который жил весь lifetime процесса и не пересоздавался. После физического отключения считывателя приложение продолжало работать со старым context, не перестраивало reader topology и не имело явного reader lifecycle.

Цель реализации: сделать автоматическое восстановление NFC внутри `Admin App` без перезапуска приложения и без поломки текущего `card-status-changed` contract.

## 2. Chosen architecture

Реализован `ReaderManager` в `admin-app/src-tauri/src/reader_manager.rs`.

Что он делает:

- держит командный `pcsc::Context` для Tauri command handlers;
- запускает отдельный background lifecycle loop для reader monitoring;
- создает и пересоздает `pcsc::Context` при runtime failures;
- выбирает активный reader и отслеживает topology/card changes;
- публикует `reader-state-changed` и сохраняет последний reader snapshot для UI bootstrap;
- продолжает публиковать `card-status-changed` в совместимом формате `{ uid, error }`.

Архитектура осталась in-process. Отдельный сервис или bridge не добавлялся.

## 3. ReaderManager state machine

Используются явные состояния:

- `scanning`
- `disconnected`
- `ready`
- `card_present`
- `recovering`
- `error`

Смысл переходов:

- `scanning` -> поиск reader после старта или после topology change;
- `disconnected` -> reader отсутствует или был потерян, но recovery loop продолжает работу;
- `ready` -> reader доступен, карта отсутствует;
- `card_present` -> reader доступен, UID считан;
- `recovering` -> context/runtime fault, выполняется recreate context;
- `error` -> unexpected runtime error, о которой UI и оператор получают явный сигнал.

Для выбора активного reader используется сохранение preferred reader name: если после rescan тот же reader снова доступен, manager возвращается к нему.

## 4. Events exposed to UI

### `card-status-changed`

Сохранен существующий контракт:

- `{ uid: "HEX_UID", error: null }` при успешном чтении карты;
- `{ uid: null, error: null }` когда reader готов, но карты нет;
- `{ uid: null, error: "..." }` когда reader потерян или идет recovery.

### `reader-state-changed`

Добавлен новый event для lifecycle:

- `state`
- `reader_name`
- `message`
- `recovering`
- `card_present`

Дополнительно добавлен Tauri command `get_nfc_reader_state`, чтобы frontend мог получить текущий snapshot сразу после старта и не зависеть от того, успел ли он поймать первый event.

## 5. Recovery logic

Реализация использует смешанную модель:

- `Context::get_status_change(...)` + `\\?PnP?\\Notification` для reader topology monitoring;
- `Context::get_status_change(...)` для card/reader state changes выбранного reader;
- прямой APDU `FF CA 00 00 00` для фактического чтения UID.

Это сознательный компромисс:

- lifecycle и topology мониторятся через нормальный PC/SC API;
- actual UID read остается на уже работающем low-level path;
- риск регрессии ниже, чем при полном переписывании всей NFC логики за один шаг.

Recovery path:

1. `ReaderManager` создает `pcsc::Context`.
2. Если readers нет, публикуется `disconnected` и manager ждет topology changes без tight loop.
3. Если reader найден, manager переходит в `ready` и запускает card monitoring.
4. При unplug/lost reader публикуется `disconnected`, `card-status-changed` переводится в error/null, polling не умирает.
5. При runtime/context faults (`InvalidHandle`, `NoService`, `ServiceStopped`, `ReaderUnavailable`, `UnknownReader`, `NoReadersAvailable`, `CommError`, `Shutdown`, `InternalError`, `UnknownError`) manager публикует `recovering`, сбрасывает context slot и создает новый context с bounded backoff.
6. После успешного recreate context manager снова сканирует readers и автоматически возвращается в `ready` или `card_present`.

Backoff:

- старт: `500 ms`
- далее экспоненциально до `4 s`
- без агрессивного tight loop.

## 6. What changed in frontend

Изменения минимальные и локальные:

- `src/stores/nfcReaderStore.js`
  - слушает и `card-status-changed`, и `reader-state-changed`;
  - делает `invoke('get_nfc_reader_state')` для initial snapshot;
  - различает `initializing`, `scanning`, `disconnected`, `recovering`, `ok`, `error`.
- `src/components/modals/NFCModal.svelte`
  - показывает отдельные состояния для `reader unavailable` и `recovering`;
  - автоматически возвращается к ожиданию карты после восстановления reader;
  - не требует перезапуска modal.
- `src/components/system/NfcReaderStatus.svelte`
  - показывает поиск, отключение, восстановление, готовность, ошибку.
- `src/components/shell/ShellStatusPills.svelte`
  - показывает `Поиск / Отключен / Восстановление / Готов / Ошибка`.
- `src/components/system/SystemFallbackBanner.svelte`
  - показывает явное сообщение при `disconnected` и `recovering`.

Текущий NFC modal flow (`uid-read`) сохранен.

## 7. UI flicker investigation and fix

### Root cause

- `ReaderManager` already deduplicated byte-identical payloads, but it still emitted different lifecycle payloads during the "reader absent" path.
- When `list_readers_internal(context)` returned an empty list, `run_context_session()` emitted `disconnected`, then called `wait_for_topology_change()`.
- `wait_for_topology_change()` returned success both for a real PC/SC topology change and for `STATUS_CHANGE_TIMEOUT`.
- After every timeout the loop emitted `scanning` again, even though topology had not changed. On the next iteration it emitted `disconnected` again.
- Result: UI received `disconnected -> scanning -> disconnected` roughly once per `2 s` timeout while no reader was connected. `nfcReaderStore.js` also called `update()` for every reader event, so Svelte re-rendered and the modal flickered.

### Fix

- Backend: `wait_for_topology_change()` now returns `true` only when `\\?PnP?\\Notification` reports a real topology change. Timeout no longer re-emits `scanning`.
- Backend: `ReaderManager` now keeps `last_emitted_reader_state` and suppresses `reader-state-changed` when the lifecycle state matches the last emitted state.
- Backend: a `300 ms` guard suppresses transient `scanning` immediately after `disconnected` or `recovering`, which stabilizes short reconnect oscillations without affecting hot-plug recovery or card detection.
- Frontend: `nfcReaderStore.js` now skips `update()` when the computed store snapshot is unchanged and debounces transient `scanning` after `disconnected/recovering`.

### UX impact

- Reader unplugged or absent: UI stays on `Считыватель отключен` without periodic blinking.
- Runtime recovery: UI stays on `Восстановление соединения...` without `recovering/scanning` flicker.
- Reader reconnected: UI transitions back to `Готов к чтению карты` once the reader is actually available again.

## 8. Risks / remaining limitations

- Автоматический hot-plug test в CI не добавлялся: физический reader нужен реально.
- Для чтения UID по-прежнему используется APDU polling on demand после reader/card state changes, а не полная event-only card pipeline.
- При редких командных гонках во время физического reconnect одноразовый Tauri command (`read_mifare_block`, `write_mifare_block`, `change_sector_keys`) может вернуть ошибку и потребовать повторить операцию, но background reader lifecycle восстанавливается автоматически.
- Если в системе несколько reader, сейчас используется один active reader за раз: повторно выбирается preferred reader, иначе первый доступный.

## 9. Manual Windows verification plan

1. App start with reader connected
   - Запустить `Admin App` при подключенном reader.
   - Проверить `NFC: Готов` и `reader-state-changed = ready`.
   - Поднести карту, убедиться, что приходит `card-status-changed.uid`.

2. App start without reader
   - Запустить приложение без reader.
   - Проверить, что UI не падает.
   - Проверить статус `Поиск` / `Считыватель отключен`.

3. Reader plugged in after app start
   - Подключить reader после запуска.
   - Убедиться, что UI автоматически переходит в `Готов`.
   - Проверить логи про обнаружение reader и возобновление мониторинга.

4. Reader unplugged while app running
   - При работающем приложении отключить reader.
   - Убедиться, что UI показывает `Отключен` или `Восстановление`.
   - Проверить лог про потерю reader.

5. Reader plugged back in while app running
   - Подключить reader обратно без перезапуска `Admin App`.
   - Убедиться, что UI автоматически возвращается в `Готов`.
   - Проверить лог `контекст PC/SC пересоздан` или повторное обнаружение reader.

6. Card read after reconnect
   - После reconnect поднести карту.
   - Убедиться, что UID снова читается штатно.

7. NFC modal recovers without app restart
   - Открыть `NFCModal`.
   - Во время открытого modal сделать unplug/replug.
   - Убедиться, что modal показывает понятное состояние `reader unavailable / recovering`, а после восстановления снова возвращается к ожиданию карты и принимает UID без закрытия приложения.
