# System Architecture v1

Date: 2026-03-10
Status: frozen for the completed M1-M7 stage

## 1. System purpose

Beer Tap System is a single-location self-pour bar platform. It controls guest access to taps, records factual pours, tracks operational balance, enforces shift discipline, and survives temporary controller/backend disconnects without double charging.

The current system is intentionally:

- visit-centric;
- backend-authoritative for operational state;
- controller-tolerant of temporary offline periods;
- POS-ready but not POS-dependent.

## 2. Core domains

### Guest

- Registered adult customer.
- Holds operational balance.
- Can have historical cards, visits, transactions, and pours.

### Visit

- Central operational aggregate.
- One guest can have only one active visit.
- Visit may open with or without a card and may receive a card later.
- Visit holds the active tap lock (`active_tap_id`) during an authorized but not yet finalized pour.

### Card

- Physical RFID token used by the controller.
- Can be active, inactive, or logically blocked through lost-card handling.
- Binding to a guest is separate from opening the visit.

### Pour

- Factual pour record.
- Created first as `pending_sync` on authorize, then finalized as `synced`, `reconciled`, or `rejected`.
- Stores factual volume, charged amount, duration, visit linkage, tap, keg, and DB-authored lifecycle timestamps.

### Transaction

- Operational money event for top-up or refund.
- Linked to guest and optionally to active visit.
- Emits POS stub notifications in the current stage.

### Shift

- Operational gate for the venue.
- Exactly one open shift is allowed.
- Open shift is required for opening visits, authorizing pours, and top-ups/refunds.
- Shift close is blocked by active visits or unresolved `pending_sync` pours.

### Keg

- Physical stock unit attached to a beverage.
- Current code uses `beverage_id`; older docs may say `beer_type_id`.
- FIFO recommendation is based on the oldest eligible unassigned keg in `status = full`.

### Lost card

- Registry of card UIDs reported as lost.
- Lost cards hard-block authorization.
- Restoration is explicit and separate from normal visit flow.

## 3. Operational flows

### Open shift

1. Operator opens a shift through `POST /api/shifts/open`.
2. Backend creates the only active shift.
3. Until a shift is open, operational endpoints remain blocked.

### Register guest

1. Operator creates or looks up a guest.
2. Guest data is stored in backend/Postgres.
3. Guest balance remains operational, not fiscal.

### Open visit

1. Operator opens a visit for an adult guest.
2. Visit becomes the active service context.
3. Card may already be provided or can be assigned later.

### Bind card

1. Operator assigns a card to an active visit.
2. Card becomes active.
3. A card cannot be reused by another active visit.

### Authorize pour

1. Controller calls `POST /api/visits/authorize-pour`.
2. Backend verifies:
   - open shift exists;
   - card is not lost;
   - active visit exists;
   - visit is not locked on another tap;
   - tap and keg are configured;
   - guest balance is sufficient for the minimum pour start;
   - backend clamp policy allows the pour.
3. Backend sets `visit.active_tap_id`, writes `lock_set_at`, creates or reuses one `pending_sync` pour row, and returns clamp data.
4. Controller opens the valve only after successful authorize.

### `pending_sync` -> `synced` / `reconciled` / `rejected`

- `pending_sync`: authorize accepted, final factual pour not yet confirmed.
- `synced`: controller later sends final pour through `/api/sync/pours`, charge is applied, lock is cleared.
- `reconciled`: operator manually finalizes an interrupted pour through `/api/visits/{visit_id}/reconcile-pour`, charge is applied, lock is cleared.
- `rejected`: previously authorized pour could not be finalized safely, for example due to insufficient funds at sync time; lock is cleared and the row is terminal.

### Close visit

1. Operator closes the visit through `POST /api/visits/{visit_id}/close`.
2. Backend refuses close while unresolved `pending_sync` exists.
3. Card is deactivated; if `card_returned=true`, the guest binding is cleared.

### X/Z reports

- X report is computed on demand for an open or closed shift.
- Z report is persisted for a closed shift and is idempotent.
- Report windows use DB time only.

## 4. Controller <-> Backend contract

### Authorize

`POST /api/visits/authorize-pour`

Successful authorize returns:

- `allowed=true`
- `min_start_ml`
- `max_volume_ml`
- `price_per_ml_cents`
- `balance_cents`
- `allowed_overdraft_cents`
- `safety_ml`
- `lock_set_at`

Controller responsibilities:

- do not open the valve without authorize success;
- enforce the returned `max_volume_ml` locally;
- treat backend as the source of truth for pour-start policy.

### Sync

`POST /api/sync/pours`

Controller sends factual data:

- `client_tx_id`
- `short_id`
- `card_uid`
- `tap_id`
- `duration_ms`
- `volume_ml`
- `price_cents`

Controller does not send authoritative official timestamps.

### Insufficient funds and lost card

- `reason="insufficient_funds"`: backend denies authorize before lock; controller must not open the valve.
- `reason="lost_card"`: backend denies authorize before lock; controller must not open the valve.
- In both cases controller enters `CARD_MUST_BE_REMOVED` until the card is physically removed and debounce passes.

### `CARD_MUST_BE_REMOVED` and `processing_sync`

- If the controller still has unsynced local pours for the tap, it treats the tap as `processing_sync` and blocks new pour start.
- If a denied card remains on the reader, controller keeps the terminal in `CARD_MUST_BE_REMOVED`.
- The controller only returns to normal scanning after reader-clear debounce.

## 5. Data and time policy

- Postgres DB time is the source of official timestamps.
- Backend writes `opened_at`, `closed_at`, `authorized_at`, `synced_at`, `reconciled_at`, and report timestamps with DB time.
- Controller sends duration and volume facts, not authoritative absolute time.
- Any legacy controller absolute timestamps are fallback input for duration calculation only.

## 6. Offline and reconcile model

- Controller can finish a pour locally and store it for later sync.
- Backend creates the operational lock and `pending_sync` row at authorize time.
- If sync arrives normally, pending becomes `synced`.
- If operator resolves timeout manually, pending becomes `reconciled` or a manual row is created idempotently.
- Late sync after reconcile is audit-only and must not create a second charge.
- Missing pending for an active lock is an anomaly: backend records audit, clears stale lock, and does not accept a new charge.

## 7. Admin app architecture

- Frontend is Svelte.
- Desktop shell is Tauri.
- Backend URL for web/dev comes from `VITE_API_BASE_URL` or `VITE_BACKEND_BASE_URL`.
- Backend URL for desktop runtime comes from persisted Tauri config with packaged default `http://cybeer-hub:8000`.
- `devUrl=http://localhost:5173` in `tauri.conf.json` is only the frontend dev server, not the backend.

## 8. Infrastructure and dev workflow

- Linux host runs backend and PostgreSQL through Docker Compose.
- Windows workstation edits code and runs `admin-app`.
- Syncthing mirrors repository changes from Windows to Linux.
- Expected Linux checkout path is `/home/cybeer/beer-tap-system`.
- Backend smoke targets are `GET /` and `GET /api/system/status`.

## 9. POS foundation

What already exists:

- `Visit` is the operational center and future POS order anchor.
- `Transaction.visit_id` and `Pour.visit_id` preserve linkage needed for later POS work.
- `backend/pos_adapter.py` defines `POSAdapter`.
- Current stub emits `notify_topup`, `notify_refund`, and `notify_pour`.
- Finalized pour notifications are deduplicated by factual pour identity.

What is explicitly postponed:

- real r_keeper or other POS adapter;
- XML payload mapping;
- outbox/retry delivery model;
- `notify_open_visit` / `notify_close_visit`;
- durable `visit <-> pos_order_id` mapping;
- fiscal deposit/refund close logic.

## 10. Known limitations and deferred work

- Real POS integration is deferred to the next phase.
- Documentation still contains historical files and some encoding debt outside the new entry points.
- `admin-app` is not fully type-clean under `svelte-check`.
- Some controller verification remains hardware-environment dependent.
- Money model is operational and intentionally not expanded into fiscal accounting in this stage.
