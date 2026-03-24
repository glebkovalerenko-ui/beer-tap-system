# Operator State Model (TapState, SessionState, IncidentState)

Дата: 2026-03-24  
Область: операторские карточки, incident-лента, backend status-коды

Этот документ фиксирует **единый словарь состояний** для UI и backend, чтобы карточки, ленты событий и API использовали одинаковые коды.

---

## 1) TapState

> Источник кодов: `taps.status` + runtime-переходы в `visit_crud`/`pour_crud`.

### 1.1 Полный список состояний

- `locked`
- `active`
- `processing_sync`
- `cleaning`
- `empty`

### 1.2 Переходы и триггеры

| From | To | Trigger type | Trigger / условие | Side effects |
|---|---|---|---|---|
| `locked` | `active` | user action | Оператор назначил кегу на кран | `keg.status -> in_use`, audit записи инвентарного действия |
| `active` | `locked` | user action | Оператор снял кегу с крана | Кран возвращается в безопасный режим, кега возвращается в `full` (если не пустая), audit |
| `active` | `processing_sync` | sync result | `authorize-pour` принят backend (создан/переиспользован `pending_sync`) | Ставится lock визита (`active_tap_id`, `lock_set_at`) |
| `processing_sync` | `active` | sync result | `pending_sync` завершён как `synced` или `reconciled`, либо lock принудительно снят | Снятие lock визита, audit для operator/sync действий |
| `processing_sync` | `active` | sync result | `pending_sync` завершён как `rejected` | Снятие lock, запись причины reject в audit |
| `active` | `empty` | device event | Подтверждено, что кега закончилась | Кега переводится в `empty`, новые продажи блокируются |
| `cleaning` | `locked`/`active` | user action | Завершён сервисный режим, кран возвращён в рабочее состояние | Возврат в рабочий lifecycle |

### 1.3 Запрещённые переходы

- `locked -> processing_sync` (без успешного authorize и lock визита).
- `empty -> processing_sync` (пока не заменена/не назначена новая кега).
- `cleaning -> processing_sync` (сервисный кран не должен авторизовывать налив).
- Любой переход в `active`, если кран без назначенной кеги.

### 1.4 Side effects

- При входе в `processing_sync`: lock визита + создание/переиспользование `pending_sync`.
- При выходе из `processing_sync`: снятие lock и нормализация tap status.
- При аномалиях синка (`sync_missing_pending`, `sync_conflict`, `sync_rejected_*`): audit event + инцидент в operator narrative/incident feed.
- При `empty`: блокировка новых продаж на кране.

### 1.5 SLA / таймауты авто-переходов

- **Автоматического таймаута `processing_sync -> active` в текущем backend нет** (переход закрывается sync/reconcile/force-unlock).
- Для контроля очереди используются operational пороги: `sync_queue` warning при `pending_sync > 0`, critical при `>= 10`.

---

## 2) SessionState

> SessionState собирается из `Visit` и связанных `Pour.sync_status` (источник для карточек сессий и narrative).

### 2.1 Полный список состояний

Код (backend):

- `not_started`
- `pending_sync`
- `synced`
- `reconciled`
- `rejected`

Дополнительный lifecycle флаг сессии (`visit_status`):

- `active`
- `closed`

### 2.2 Переходы и триггеры

| From | To | Trigger type | Trigger / условие | Side effects |
|---|---|---|---|---|
| `not_started` | `pending_sync` | sync result | Успешный `authorize-pour`: создан `pending_sync` и выставлен lock | `active_tap_id`, `lock_set_at`, audit authorize |
| `pending_sync` | `synced` | sync result | Контроллер прислал фактический pour, backend подтвердил charge | Баланс/объём обновлены, lock снят |
| `pending_sync` | `reconciled` | user action | Оператор вызвал `reconcile-pour` | Ручная фиксация продажи, lock снят, audit reconcile |
| `pending_sync` | `rejected` | sync result | Синк не может быть безопасно принят (`zero_volume`, insufficient funds, mismatch и т.п.) | Терминальный reject, lock снят, audit причины |
| `active` (`visit_status`) | `closed` (`visit_status`) | user action | Оператор закрывает визит | Карта деактивируется/отвязывается по правилам, audit close |

### 2.3 Запрещённые переходы

- `closed -> active` (ре-открытие закрытого визита не поддерживается).
- `pending_sync -> not_started` (rollback состояния назад не допускается).
- `rejected -> synced/reconciled` для того же `pending_sync` (терминальный reject).
- `visit close`, если есть `pending_sync` по визиту.

### 2.4 Side effects

- Создание incident-like сигналов в session history при `sync_missing_pending`, `sync_conflict`, `late_sync_*`, `lost_card_blocked`, `insufficient_funds_*`.
- Блокировка параллельного налива через visit lock.
- Полный audit trail операторских вмешательств (`force_unlock`, `reconcile`, блокировки по карте/балансу).

### 2.5 SLA / таймауты авто-переходов

- **Авто-таймаут закрытия `pending_sync` не зашит**; закрытие делается через sync payload, manual reconcile, либо force-unlock.
- Operational SLA: `pending_sync` должен быть закрыт до закрытия визита/смены (иначе backend блокирует close).

---

## 3) IncidentState

> IncidentState хранится в overlay-таблице `incident_states` и накладывается на агрегированные инциденты из system/audit/flow источников.

### 3.1 Полный список состояний

- `new`
- `in_progress`
- `closed`

### 3.2 Переходы и триггеры

| From | To | Trigger type | Trigger / условие | Side effects |
|---|---|---|---|---|
| `new` | `in_progress` | user action | `POST /api/incidents/{id}/claim` (назначение owner) | `owner`, `last_action=claim`, audit `incident_claim` |
| `new` | `in_progress` | user action | `POST /api/incidents/{id}/escalate` | `escalated_at`, `escalation_reason`, audit `incident_escalate` |
| `in_progress` | `in_progress` | user action | Добавление note/escalate | Обновление note/action timestamps + audit |
| `in_progress` | `closed` | user action | `POST /api/incidents/{id}/close` | `closed_at`, `closure_summary`, audit `incident_close` |
| source-derived `in_progress` | `closed` | sync result / device event | Для flow-инцидента выставлен `finalized_at` в `non_sale_flows` | В агрегаторе статус становится `closed` |

### 3.3 Запрещённые переходы

- `closed -> in_progress/new` (reopen не реализован API).
- `new -> closed` без явного `close` действия оператора (в overlay модели).

### 3.4 Side effects

- Любое действие (`claim`, `note`, `escalate`, `close`) пишет audit (`incident_*`).
- `escalate` добавляет метаданные эскалации (`escalated_at`, `escalation_reason`).
- `close` фиксирует resolution summary для отчётности.

### 3.5 SLA / таймауты авто-переходов

- Авто-закрытия по TTL в overlay-модели нет.
- Operational мониторинг устройств в system summary:
  - контроллер считается `critical`, если heartbeat отсутствует или старше 15 минут;
  - backlog `pending_sync` влияет на критичность `sync_queue` (`>0` warning, `>=10` critical).

---

## 4) Единая таблица: UI status ↔ backend status codes

> Использовать как словарь для карточек (session/tap/incident) и event feed.

| UI scope | UI status (что рисуем) | Backend code(s) | Где брать в API/данных |
|---|---|---|---|
| Tap card | Ready | `tap.status=active` | `tap.status` |
| Tap card | Busy / Syncing | `tap.status=processing_sync` | `tap.status` |
| Tap card | Locked | `tap.status=locked` | `tap.status` |
| Tap card | Maintenance | `tap.status=cleaning` | `tap.status` |
| Tap card | Empty | `tap.status=empty` | `tap.status` |
| Session card | Active | `visit_status=active` и `sync_state in {not_started,synced,reconciled}` | Session history item |
| Session card | Waiting for sync | `sync_state=pending_sync` | Session history item |
| Session card | Needs attention | `sync_state=rejected` или `has_incident=true` | Session history item |
| Session card | Closed OK | `visit_status=closed` и `sync_state in {synced,reconciled,not_started}` | Session history item |
| Session card | Interrupted | `visit_status=closed` + `closed_reason` not in `{guest_checkout,operator_close,manual_close}` | Session history item |
| Incident feed | New | `incident.status=new` | `/api/incidents` |
| Incident feed | In progress | `incident.status=in_progress` | `/api/incidents` |
| Incident feed | Closed | `incident.status=closed` | `/api/incidents` |
| System health chip | OK | `overall_state=ok` или subsystem `state=ok` | `/api/system/summary` |
| System health chip | Warning | `overall_state=warning` или subsystem `state=warning` | `/api/system/summary` |
| System health chip | Critical | `overall_state=critical` или subsystem `state=critical` | `/api/system/summary` |

### Нормализация для UI

- В event feed хранить **backend code как canonical value**, UI-лейбл строить через i18n-словарь.
- Не сериализовать только человекочитаемые русские лейблы (`Активна`, `Требует внимания` и т.д.) без machine-code.
- Для фильтров и аналитики использовать коды (`pending_sync`, `rejected`, `in_progress`, `critical`) как первичный ключ группировки.
