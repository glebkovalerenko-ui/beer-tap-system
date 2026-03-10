# Controller Flow Tail And Anomaly RCA

## 1. Problem statement

Наблюдался риск, что flow meter продолжает накапливать импульсы после закрытия клапана, но контроллер завершает pour слишком рано. Из-за этого хвост фактического отпуска не относится к текущему наливу и может быть считан уже в следующем авторизованном pour.

Второй системный дефект: при закрытом клапане контроллер почти не наблюдал датчик потока. Поэтому flow вне активного налива не классифицировался ни как нормальный хвост, ни как инцидент.

## 2. Current implementation behavior

До исправления контроллер работал так:

- `FlowManager.process()` создавал pour только после успешного `authorize_pour`.
- Клапан открывался сразу после авторизации.
- Flow meter читался только внутри узкого внутреннего цикла `while self.hardware.is_card_present()`.
- `hardware.get_volume_liters()` возвращал дельту и сразу обнулял `pulse_count`.
- Как только внутренний цикл заканчивался, сессия считалась завершённой сразу же: клапан закрывался, локальный pour записывался, затем вызывался `reset_pulses()`.
- В sync payload уходили только `client_tx_id`, `short_id`, `card_uid`, `tap_id`, `duration_ms`, `volume_ml`, `price_cents`.

Итоговое поведение до фикса:

- `valve open + card present + flow`: объём учитывался корректно.
- `valve closed + card present + flow`: контроллер уже не читал датчик, объём не относился к текущему pour.
- `valve closed + no card + flow`: контроллер не читал датчик, объём копился в `pulse_count`.
- `valve closed + card present + no session + flow`: контроллер не читал датчик, объём тоже копился до следующего чтения.

## 3. Root cause analysis

Корневая причина была составной:

1. Жизненный цикл pour был привязан к команде закрытия клапана, а не к фактическому окончанию потока.
2. `get_volume_liters()` вызывался только в active-pour path, а не постоянно.
3. После выхода из pour-loop не существовало состояния `drain_tail` или аналогичного окна затухания.
4. После записи текущего pour контроллер вызывал `reset_pulses()`, но только один раз, сразу после завершения сессии.
5. Любые импульсы, пришедшие уже после этого `reset_pulses()`, нигде не обслуживались, пока не стартует следующий авторизованный pour.
6. Первый `get_volume_liters()` следующего pour забирал накопившийся хвост, поэтому объём логически “переезжал” в следующую сессию.

Отдельный архитектурный gap:

- backend не отличал обычный объём от хвоста налива;
- если фактический объём выходил за авторизованный баланс из-за хвоста после закрытия клапана, старый backend-path мог перевести такой sync в `rejected_insufficient_funds`, хотя это был реальный отпуск внутри уже начатого налива.

## 4. Scenario matrix

| Valve state | Card state | Session state | Flow present | Expected behavior | Current behavior before fix | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| Open | Present | Active authorized | Yes | Count into current pour | Counted in current pour | Нет |
| Closed | Present | Same pour just closed | Yes | Keep pour open in tail window and count into same guest | Session already finalized, flow not read | Хвост терял связь с текущим pour |
| Closed | No card | No active session | Yes | Do not charge guest, create anomaly/incident | Flow ignored until future read | Нет детекта, возможен перенос в следующий pour |
| Closed | Present | No valid session / blocked / denied | Yes | Do not charge guest, create anomaly/incident | Flow ignored while waiting for card removal | Нет детекта, возможен перенос в следующий pour |
| Closed | Present or absent | No active session | No | Idle state | Idle state | Нет |

## 5. Solution options

### Option 1. Minimal patch

Как работает:

- после команды закрытия клапана контроллер ещё короткое время дочитывает датчик;
- весь post-close flow добавляется в текущий pour;
- остальная логика не меняется.

Плюсы:

- минимальный объём изменений;
- низкий риск для M4 offline sync и dedupe;
- быстро убирает основной перенос хвоста.

Минусы:

- нет постоянного мониторинга flow при закрытом клапане;
- нет backend incident event;
- over-limit tail всё ещё конфликтует с M6 insufficient-funds reject path.

Риск регрессий:

- низкий в контроллере;
- средний, если попытаться без контракта отправлять фактический over-limit volume на backend.

Изменения в коде:

- только `rpi-controller/flow_manager.py`.

Совместимость с архитектурой:

- полезный hotfix, но не закрывает полную целевую модель 4 сигналов.

### Option 2. State-machine fix

Как работает:

- вводятся явные состояния `idle`, `pouring`, `drain_tail`, `card_wait_removal`;
- pour завершается не на `valve_close`, а после затухания потока;
- closed-valve flow вне активной сессии считается anomaly.

Плюсы:

- точно решает root cause;
- хорошо ложится на требуемую модель “valve + card + session + flow”;
- локализован в controller domain.

Минусы:

- больше логики и тестовых веток в `FlowManager`;
- требует аккуратной настройки таймингов на железе.

Риск регрессий:

- средний в controller loop;
- низкий для M4/M5/M7, если sync contract не трогать.

Изменения в коде:

- `rpi-controller/flow_manager.py`;
- тесты контроллера.

Совместимость с архитектурой:

- хорошая;
- это естественная эволюция текущего single-loop контроллера.

### Option 3. Full anomaly-monitoring layer

Как работает:

- flow meter мониторится постоянно как отдельный доменный источник событий;
- pour lifecycle и anomaly lifecycle разделяются;
- backend получает отдельные controller flow events/incidents;
- Admin App строит alerting поверх этих событий.

Плюсы:

- лучшая долгосрочная архитектура;
- легко расширять под утечки, залипание клапана, дребезг датчика, диагностику железа;
- не смешивает бизнес-учёт pour и аппаратные инциденты.

Минусы:

- больше скоуп;
- потребует отдельного event model / UI integration / possibly polling or push;
- выше стоимость регрессий и внедрения.

Риск регрессий:

- средний/высокий из-за ширины изменений.

Изменения в коде:

- controller loop;
- backend contract;
- potentially Admin App.

Совместимость с архитектурой:

- отличная как target-state, но избыточно как первый фикс.

## 6. Recommended solution

Рекомендуемый вариант: Option 2 с маленьким контрактным расширением backend.

Причина:

- простой `grace window` без anomaly-layer не закрывает проблему closed-valve flow вне сессии;
- полноценный отдельный subsystem пока слишком широк;
- state-machine-lite с `drain_tail` решает реальный RCA локально и безопасно;
- дополнительное поле `tail_volume_ml` в sync payload позволяет backend отличить базовый объём от хвоста и не ломать M6 reject path для обычных insufficient-funds cases.

Реализованная схема:

- контроллер читает flow и после `valve_close`, пока не наступит окно стабилизации;
- весь post-close объём относится к текущему pour;
- over-limit часть, возникшая в момент закрытия по лимиту, тоже помечается как хвост текущего pour;
- локальный journal и sync payload получили `tail_volume_ml`;
- backend разрешает отрицательный баланс только на хвостовую часть, если базовый объём укладывается в баланс;
- closed-valve flow вне активной сессии отправляется как `controller_flow_anomaly` в audit log через internal endpoint.

## 7. Risk analysis

Основные риски:

- нужно откалибровать `FLOW_TAIL_IDLE_SECONDS` и `FLOW_TAIL_MAX_SECONDS` на реальном железе;
- датчик может давать шум, поэтому порог `CLOSED_VALVE_FLOW_REPORT_MIN_VOLUME_ML` может потребовать тюнинга;
- backend теперь доверяет `tail_volume_ml` как internal-controller полю, поэтому это предположение держится на доверенной internal token boundary;
- Admin App пока не получил отдельный live-alert UI, только backend audit event, который уже можно читать и показывать.

Что не должно ломаться и почему:

- M4 offline sync / pending_sync / reconcile: контракт остался совместимым, dedupe по `client_tx_id` не менялся;
- M5 shifts / reports: pours и audit logs продолжают писаться в прежние сущности;
- M6 insufficient funds: обычный reject path сохранён, исключение сделано только для явно помеченного хвоста;
- M7 POSAdapter seam: финализация accepted pour по-прежнему проходит через `process_pour()` и `notify_pour()`.

## 8. Implementation plan

Реализовано:

- `rpi-controller/flow_manager.py`
  - добавлено post-close `drain_tail` окно;
  - добавлен closed-valve flow monitor;
  - убран опасный end-of-session `reset_pulses()`, reset перенесён на старт нового pour;
  - локальный pour теперь хранит `tail_volume_ml`.
- `rpi-controller/database.py`
  - добавлена additive local migration для `tail_volume_ml`.
- `rpi-controller/sync_manager.py`
  - в sync payload добавлен `tail_volume_ml`;
  - добавлен `report_flow_anomaly()`.
- `backend/schemas.py`
  - `PourData.tail_volume_ml`;
  - schemas для controller flow anomaly endpoint.
- `backend/api/controllers.py`
  - добавлен internal endpoint `/api/controllers/flow-events`.
- `backend/crud/pour_crud.py`
  - added tail-aware insufficient-funds handling;
  - хвост допускается в минус только если базовый объём укладывается в баланс;
  - audit action `sync_tail_overdraft_accepted`.
- Тесты:
  - controller tail accounting and anomaly detection;
  - backend flow anomaly endpoint;
  - backend M6 tail-overdraft accept path.

## 9. Verification plan

Автотесты:

- `python -m pytest rpi-controller/test_flow_manager.py -q`
- `docker exec beer_backend_api sh -lc "cd /app && pytest tests/test_controller_flow_events.py tests/test_m6_insufficient_funds_clamp.py -q"`
- `python scripts/encoding_guard.py --all`

Проверка на железе:

1. Авторизовать pour, снять карту сразу после закрытия клапана, убедиться, что хвост попал в тот же `short_id`.
2. Довести pour до авторизационного лимита и проверить, что хвост попал в тот же pour, а не в следующий.
3. При закрытом клапане и без карты сгенерировать flow и убедиться, что guest не затронут, а на backend появился `controller_flow_anomaly`.
4. При закрытом клапане и вставленной, но невалидной карте сгенерировать flow и убедиться в таком же anomaly path.
5. Проверить, что после anomaly следующий нормальный pour стартует с нуля и не получает старый объём.
6. Проверить в Admin/App backend audit feed, что оператор видит `controller_flow_anomaly` и `sync_tail_overdraft_accepted`.

Оставшийся follow-up:

- если нужен именно live alert в Admin App, поверх audit feed нужно добавить отдельный UI/polling path; backend event для этого уже есть.
