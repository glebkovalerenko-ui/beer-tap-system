# TAP Display `processing_sync` RCA

## 1. Problem statement

On March 16, 2026, the real Tap Display screen on the Raspberry Pi showed a persistent service state:

- `Сервисное состояние`
- `Подождите`
- `Кран завершает синхронизацию`
- operator code `processing_sync`

The screen stayed in that state for hours and did not return to normal idle content.

## 2. Live evidence collected

### Raspberry Pi controller (`cybeer@192.168.0.114`)

- `beer-tap-controller.service` and `tap-display-agent.service` were both `active/running` since `2026-03-16 09:11:10 MSK`.
- `/etc/beer-tap/device.env` confirmed `TAP_ID=1` and `SERVER_URL=http://192.168.0.110:8000`.
- `/run/beer-tap/display-runtime.json` showed controller runtime `phase="idle"` with fresh timestamps, not `blocked` and not stale.
- `GET http://127.0.0.1:18181/local/display/runtime` showed:
  - `runtime.phase="idle"`
  - `health.backend_link_lost=false`
  - `health.controller_runtime_stale=false`
- `GET http://127.0.0.1:18181/local/display/bootstrap` showed, before repair:
  - `snapshot.tap.status="processing_sync"`
  - cached snapshot otherwise healthy
- Local controller queue file `/home/cybeer/beer-tap-system/rpi-controller/local_journal.db` had:
  - `status_counts []`
  - `unsynced_for_tap1 0`
  - no local unsynced pour rows at all
- Controller journal for the latest real interaction on March 16 showed:
  - `2026-03-16 10:52:17 MSK` authorize accepted for card `0b24b1cd` with `лимит 90 мл`
  - progress stayed at `0 мл`
  - `2026-03-16 10:52:19 MSK` valve closed with `reason=card_removed`
  - session ended with `Налито: 0 мл`

### Backend / hub (`cybeer@192.168.0.110`)

- `GET /api/display/taps/1/snapshot` returned, before repair:
  - `tap.status="processing_sync"`
- Live DB state before repair:
  - `taps.tap_id=1 status='processing_sync'`
  - active visit `d68bac03-42b3-4105-81f4-e18327d16785`
  - `visits.active_tap_id=1`
  - `visits.lock_set_at='2026-03-16T07:52:16.912633+00:00'`
  - one and only one system-wide `pending_sync` row:
    - `client_tx_id='pending-sync:d68bac03-42b3-4105-81f4-e18327d16785:1:1f2ce151'`
    - `tap_id=1`
    - `card_uid='0b24b1cd'`
    - `volume_ml=0`
    - `authorized_at='2026-03-15T15:51:16.172551+00:00'`
- Backend logs showed:
  - first creation at `2026-03-15 15:51:16 UTC`:
    - `authorize_pour ... outcome=pending_created`
  - repeated later authorizations for the same card/visit/tap:
    - `2026-03-15 16:00:37 UTC ... outcome=pending_exists`
    - many more `pending_exists` on March 15
    - `2026-03-16 06:13:42 UTC ... outcome=pending_exists`
    - `2026-03-16 07:52:17 UTC ... outcome=pending_exists`
- No matching accepted `/api/sync/pours` evidence existed for that pending row.

### Relevant code path evidence

- Display client state precedence:
  - [`tap-display-client/src/display-state.js`](c:\Users\CatNip420\Documents\Projects\beer-tap-system\tap-display-client\src\display-state.js)
  - if runtime is not blocked, but backend snapshot has `tap.status="processing_sync"`, client resolves `tap_service_state -> processing_sync`
- Backend authorize path:
  - [`backend/crud/visit_crud.py`](c:\Users\CatNip420\Documents\Projects\beer-tap-system\backend\crud\visit_crud.py)
  - `authorize-pour` sets `visit.active_tap_id`, `lock_set_at`, may move tap to `processing_sync`, and creates or reuses one `pending_sync` row
- Controller finalize path:
  - [`rpi-controller/flow_manager.py`](c:\Users\CatNip420\Documents\Projects\beer-tap-system\rpi-controller\flow_manager.py)
  - local journal row is added only when `total_volume_ml > 1`
  - zero-volume / near-zero aborted sessions do not create a local sync artifact

## 3. State-source analysis

The live source of the on-screen `processing_sync` was the backend snapshot, not the controller runtime.

Chain before repair:

1. Controller runtime on Pi was healthy and `idle`.
2. Display agent runtime endpoint correctly exposed that idle runtime.
3. Display agent bootstrap snapshot still carried backend `tap.status="processing_sync"`.
4. Display client precedence treated that backend tap status as a service state.
5. The screen therefore honestly rendered `processing_sync`.

This was a real backend-side stuck state, not a display mapping bug and not a false boot/loading state.

## 4. Expected sync completion path

Under the current backend/controller contract:

1. `POST /api/visits/authorize-pour` creates or reuses one backend `pending_sync` row and locks the visit.
2. Controller later stores the factual pour locally.
3. Sync worker sends `/api/sync/pours`.
4. Backend updates the pending row to `synced` or another terminal state.
5. Backend clears:
   - `visits.active_tap_id`
   - `visits.lock_set_at`
   - `taps.status` back to `active` unless keg became empty

What actually happened in this incident:

1. Backend created a `pending_sync` row on authorize.
2. The real controller session poured `0 мл`.
3. Controller therefore created no local journal row.
4. Because no local row existed, no `/api/sync/pours` payload could ever be sent for that session.
5. Backend therefore had no normal event that could terminate the pending row and clear `processing_sync`.

## 5. Root cause

The stuck state was caused by a contract/logic gap between backend authorize semantics and controller local journaling semantics:

- backend creates/reuses `pending_sync` at authorize time, before factual pour data exists
- controller only persists a local sync artifact when factual poured volume exceeds `1 мл`
- a zero-volume authorize-abort session therefore leaves:
  - backend `pending_sync`
  - visit lock
  - tap `processing_sync`
  - but no controller-side local record capable of ever completing sync

That is why the system stayed stuck for hours:

- the backend status was legitimate relative to its own stored state
- but that stored state was orphaned and had no exit path

Additional confirming fact:

- backend continued to return `authorize_pour ... outcome=pending_exists` for the same visit/tap on later card presentations, so the lock state kept being reused instead of cleared

## 6. Fix applied or recommended next action

### Live recovery applied

On March 16, 2026, a targeted backend recovery was applied for the single confirmed orphaned row:

- specific row `pending-sync:d68bac03-42b3-4105-81f4-e18327d16785:1:1f2ce151`
- confirmed `volume_ml=0`
- confirmed no local controller queue row existed

Recovery action:

- mark that pending row `sync_status='rejected'`
- clear `visits.active_tap_id`
- clear `visits.lock_set_at`
- return `taps.status` to `active`
- add audit entry `manual_pending_cancel_no_pour`

### Recommended durable follow-up

A code-level preventive fix is still needed. The current contract can recreate the same incident.

Safe follow-up directions:

1. Add an explicit zero-volume cancel/abort path from controller to backend so an authorize without factual pour can terminate its `pending_sync` row.
2. Or redesign the contract so backend does not create a durable `pending_sync` row until factual local pour data exists.

This should be treated as a follow-up sync-contract fix, not as cosmetic display work.

## 7. Post-investigation verification

After the live recovery:

- backend snapshot for Tap 1 returned `tap.status="active"`
- Pi `GET /local/display/runtime` still returned `runtime.phase="idle"`
- Pi `GET /local/display/bootstrap` returned `snapshot.tap.status="active"`
- backend DB showed:
  - `taps.status='active'`
  - `visits.active_tap_id=NULL`
  - `visits.lock_set_at=NULL`
  - repaired row now `sync_status='rejected'`

This means the display chain no longer has any source that can legitimately render `processing_sync`.

## 8. Final verdict

`PROCESSING_SYNC ROOT CAUSE IDENTIFIED, FOLLOW-UP FIX NEEDED`

Why:

- the live stuck instance was fully explained and manually cleared
- the real source was a backend orphaned `pending_sync` state, not a display bug
- however, the underlying zero-volume authorize-abort gap still exists in the current code contract and can recur until a durable sync-path fix is implemented
