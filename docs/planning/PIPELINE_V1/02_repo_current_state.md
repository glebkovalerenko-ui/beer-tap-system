# Repo Current State Reconnaissance

Scope: inventory of the current codebase behavior relevant to `OPERATIONAL_MODEL_V1`.

## 1) Architecture map (components + responsibilities)

## 1.1 Backend API (FastAPI + SQLAlchemy)
- **Location**: `backend/`
- **Entrypoint**: `backend/main.py`.
- **Responsibilities now**:
  - CRUD for guests/cards/taps/kegs/beverages.
  - Pour ingestion from controllers via batch sync endpoint (`/api/sync/pours`).
  - Emergency-stop global flag.
  - Controller registration/check-in.
  - JWT + internal-token auth.
  - Basic audit log persistence.

## 1.2 Admin app (Svelte + Tauri)
- **Location**: `admin-app/`
- **UI shell**: `admin-app/src/App.svelte`.
- **Routes now**: dashboard, guests, taps-kegs, login.
- **Responsibilities now**:
  - Guest operations (create/update, card bind, top-up, history view hooks).
  - Keg/tap inventory management and assignment.
  - Emergency stop toggle.
  - Basic shift open/close UX via localStorage store (client-side only, no backend model).

## 1.3 Controller app (RPi Python)
- **Location**: `rpi-controller/`
- **Entrypoint**: `rpi-controller/main.py`.
- **Responsibilities now**:
  - Read NFC card UID + flow pulses; open/close valve while card present.
  - Write local pour journal to SQLite (`local_journal.db`).
  - Periodic sync to backend (`/api/sync/pours`).
  - Emergency-stop polling (`/api/system/status`).
  - Card authorization by scanning `/api/guests` and matching card list.

## 1.4 Runtime communication
- Admin app (Svelte/Tauri) -> backend API via JWT bearer.
- Controller -> backend API via `X-Internal-Token`.
- No message bus; all integration is HTTP request/response.

## 2) Directory map with key files

## 2.1 Backend
- `backend/main.py` — app assembly + `/api/token` + `/api/sync/pours`.
- `backend/models.py` — DB entities: Beverage, Keg, Tap, Guest, Card, Pour, Transaction, AuditLog, Controller, SystemState.
- `backend/schemas.py` — API payload/response schemas.
- `backend/api/*.py` — route modules.
- `backend/crud/*.py` — data logic (pour processing, assignments, topups, audit, etc.).
- `backend/security.py` — JWT/internal token auth and background audit trigger.
- `backend/alembic/` — alembic scaffold exists, but no versions in repo.

## 2.2 Admin app
- `admin-app/src/App.svelte` — routing and shell.
- `admin-app/src/routes/*.svelte` — page routes.
- `admin-app/src/stores/*.js` — state stores (guest/tap/keg/pour/system/shift/role/session).
- `admin-app/src-tauri/src/main.rs` + `api_client.rs` — Tauri command bridge + HTTP client.

## 2.3 Controller
- `rpi-controller/main.py` — loop + sync worker thread.
- `rpi-controller/flow_manager.py` — pour capture loop and local record creation.
- `rpi-controller/database.py` — SQLite schema for local unsynced pours.
- `rpi-controller/sync_manager.py` — sync/auth/status polling against backend.
- `rpi-controller/config.py` — tap id, server URL, internal token.

## 3) Current data models (as implemented)

## 3.1 Backend persistent entities
Implemented entities:
- Beverage, Keg, Tap.
- Guest, Card.
- Pour, Transaction.
- Controller.
- SystemState (key-value flags, currently used for emergency stop).
- AuditLog.

Not implemented as first-class backend entities:
- Visit, LostCard, Shift/ShiftMember, Alert, Location, POSAdapter record model.

## 3.2 Status fields currently used
- Card: `active/inactive/lost`.
- Tap: `active/locked/cleaning/empty`.
- Keg: `full/in_use/empty`.
- Pour sync in backend: no explicit `sync_status` column; sync inferred from controller journal status and accepted rows.

## 3.3 Controller local SQLite
`pours` table fields:
- `client_tx_id`, `card_uid`, `tap_id`, `start_ts`, `end_ts`, `volume_ml`, `price_cents`, `status` (`new|confirmed|failed`), `attempts`, `price_per_ml_at_pour`.

## 4) Current endpoints inventory

## 4.1 System/auth/sync
- `POST /api/token`
- `GET /`
- `POST /api/sync/pours`
- `GET /api/system/status`
- `POST /api/system/emergency_stop`
- `GET /api/system/states/all` (hidden in schema)

## 4.2 Operational CRUD
- Guests: create/list/get/update, bind/unbind card, top-up, history.
- Cards: create/list/update status.
- Taps: create/list/get/update/delete, assign/unassign keg.
- Kegs: create/list/get/update/delete.
- Beverages: create/list/get.
- Pours: read recent list.
- Controllers: register, list.
- Audit: list.

## 5) Current UI routes/screens
- `/` Dashboard:
  - emergency stop toggle,
  - shift open/close (frontend-local),
  - taps status widget,
  - pour feed.
- `/guests`:
  - guest search/list/detail,
  - create/edit guest,
  - bind card via NFC modal,
  - top-up modal (blocked if local shift not open).
- `/taps-kegs`:
  - taps grid,
  - assign keg modal,
  - keg list/form,
  - beverage manager.
- Login screen with Tauri command fallback to direct HTTP.

## 6) Current controller-to-backend protocol
- **Card auth**: controller calls `GET /api/guests`, scans guest cards for UID match.
- **Emergency-stop check**: `GET /api/system/status`.
- **Pour sync**: `POST /api/sync/pours` batch payload; per-row accepted/rejected response with reason.
- **Controller registration**: endpoint exists (`/api/controllers/register`) but not called in current `rpi-controller` code path.

## 7) Current alerting, keg logic, auth/role, logging/audit

## 7.1 Alerting and keg logic
- No Alert entity or alert API.
- Keg depletion currently affects statuses (`keg->empty`, `tap->empty`) during pour processing.
- No severity thresholds (<20/<10/critical) and no acknowledge/resolve workflow.
- No FIFO recommendation engine for keg replacement.

## 7.2 Auth and roles
- Backend auth: JWT + internal token.
- User storage: hardcoded single fake user (`admin/fake_password`) in backend security module.
- Backend RBAC: none.
- Frontend roleStore has local role presets (owner/manager/bartender) for UI gating only; not server-enforced.

## 7.3 Logging/audit
- Python logging configured in backend entrypoint.
- Audit entries stored in `audit_logs` table.
- `security.get_current_user` enqueues background audit for POST/PUT/DELETE requests using method+path action.
- No dedicated operational event log for visit/pour authorization decisions (e.g., simultaneous card use denial).

## 8) Current flows supported end-to-end

Supported now:
1. Staff logs in (JWT).
2. Staff creates guest.
3. Staff binds card to guest.
4. Staff tops up balance.
5. Staff configures beverages/kegs/taps and assigns keg to tap.
6. Controller reads card -> allows pour if card exists in guest list.
7. Controller records pour locally and syncs batch to backend.
8. Backend validates card/tap/keg/balance and stores Pour + deducts guest balance + deducts keg volume.
9. Dashboard can display recent pours and equipment state.

Partially supported:
- Offline-first pour capture exists in controller local DB, but backend lacks `pending_sync`/tap `processing_sync` semantics.
- Shift UX exists in frontend only; not operationally authoritative.

## 9) Gaps vs OPERATIONAL_MODEL_V1

Major mismatch areas:
1. **No Visit model/lifecycle** (active visit invariant, card deactivation on closure, `active_tap_id`).
2. **No LostCard registry model**; only card status string exists.
3. **No Alert domain** (severity matrix, ack/resolve, unresolved queues).
4. **No Shift backend model/wizard gates**; only local UI approximation.
5. **No PourSession sync-status model in backend** (`pending_sync`/`synced`).
6. **No tap state `processing_sync`**.
7. **No explicit simultaneous-use prevention via `active_tap_id`**.
8. **No FIFO keg replacement recommendation engine by warehouse timestamps.**
9. **No POSAdapter interface boundary implemented as explicit contract object/service in code.**
10. **No Location model, and no explicit multi-location-ready linkage in current operations.**

Assumption note:
- Existing architecture can be evolved incrementally (additive schema + APIs + UI flows) without full rewrite; this plan is built around that assumption.
