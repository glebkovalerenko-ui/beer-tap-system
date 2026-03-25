# Beer Tap System

Beer Tap System is a self-pour bar platform for a single location. The current frozen stage covers M1-M7: visit-centric operations, controller/backend sync, shift discipline, lost-card handling, FIFO keg recommendation, and a POS-ready stub seam. Real POS or r_keeper integration is not part of this stage.

## Current stage

- M1: Alembic baseline and migration discipline.
- M2-M3.5: visit model, active tap lock semantics, open/bind/close visit flow.
- M4: offline sync, `pending_sync`, manual reconcile, no-double-charge behavior.
- M5: shift operational mode, X/Z reports, DB-time policy.
- M6: insufficient funds clamp, rejected sync terminal path, lost cards, controller terminal UX hardening.
- M7: FIFO keg recommendation and backend POS adapter stub.

## Main components

- `backend/`: FastAPI + SQLAlchemy + Alembic. This is the operational source of truth.
- `rpi-controller/`: Raspberry Pi tap controller with local SQLite queue and sync loop.
- `admin-app/`: Svelte + Tauri operator/admin application.
- `docker-compose.yml`: Linux runtime for backend + PostgreSQL.

## Architecture in one paragraph

`Visit` is the central operational aggregate. `Transaction` records top-up and refund events, `Pour` records the factual pour lifecycle, `Shift` gates operational activity, and `Card` plus `LostCard` model RFID issuance and recovery. The controller is decoupled from POS and talks only to the backend. POS is represented only by a stub seam (`notify_topup`, `notify_refund`, `notify_pour`) so the core remains POS-ready but not POS-dependent.

## Development topology

- Windows workstation: edit code locally and run `admin-app`.
- Linux host: run `docker compose` for backend + PostgreSQL.
- Syncthing: sync repository from Windows to Linux.

This repository is optimized around that split. The backend is expected to run from the Linux checkout; the admin app is expected to run locally on Windows.

## Quick start

### Backend

```bash
cd /home/cybeer/beer-tap-system
cp .env.example .env
docker compose up -d --build
docker compose exec -T beer_backend_api python -m alembic current
curl -fsS http://localhost:8000/
curl -fsS http://localhost:8000/api/system/status
```

### Admin app

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
cd admin-app
npm ci
npm run dev
```

### Controller

Controller code lives in `rpi-controller/`. It authorizes pours through the backend, stores unsynced pours locally, and pushes them later through `/api/sync/pours`.

## Read next

- `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`
- `docs/architecture/OPERATIONAL_MODEL_V1.md`
- `docs/API_REFERENCE.md`
- `docs/dev/SYNCTHING_DEV_RUNBOOK.md`
- `docs/dev/ADMIN_APP_BACKEND_URL.md`
- `docs/reports/STAGE_COMPLETION_VERDICT_PRE_NEXT_PHASE.md`
- `docs/admin-app/07-operator-core-phase-1-result.md`

## Stage boundary

- POS/r_keeper foundation is prepared.
- Real POS integration is intentionally deferred.
- Controller and POS remain decoupled through the backend seam.
