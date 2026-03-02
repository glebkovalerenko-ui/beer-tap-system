# TILT_STABILIZATION_REPORT

## 1. Context

- Repo: `beer-tap-system`
- Target topology: Docker/Tilt runs on Linux host `cybeer-hub`; admin-app and RPi controllers talk to backend at `http://cybeer-hub:8000`.
- Internal container topology stays unchanged: backend reaches Postgres at `postgres:5432`.
- `cybeer-hub` resolved from the current workstation to `192.168.0.110` via local name resolution during DIAG.

## 2. Root causes

### backend-db

- Root cause: backend startup depended only on Postgres container health and did not guarantee schema readiness.
- On `master`, backend had no entrypoint migration bootstrap and no startup validation that DB revision matched Alembic head.
- `/api/system/status` touches the database, so backend could look "up" while still failing on the first real request.

### admin-app-url

- Root cause: backend URL was split across multiple layers, with `localhost` hardcoded in live code.
- Web login/API helper still used `http://localhost:8000`.
- Tauri Rust client still used `http://localhost:8000/api`.
- Result: changing only one JS file could not change all runtime paths.

### controller-url

- Root cause: controller defaulted to the old static IP instead of `cybeer-hub`, and startup logs did not expose the real target or DNS result.
- When requests failed, logs were too weak to tell whether the problem was DNS, wrong host, or backend reachability.

## 3. Fixes

### Backend and Tilt

- [`backend/Dockerfile`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/Dockerfile)
  Added an entrypoint so every container start runs migration bootstrap before `uvicorn`.
- [`backend/entrypoint.sh`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/entrypoint.sh)
  Logs redacted `DATABASE_URL`, runs `python -m alembic upgrade head`, then starts backend on `0.0.0.0:8000`.
- [`backend/startup_checks.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/startup_checks.py)
  Verifies DB connectivity and that current revision matches Alembic head.
- [`backend/main.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/main.py)
  Calls startup verification during FastAPI lifespan.
- [`backend/database.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/database.py)
  Makes `DATABASE_URL` mandatory.
- [`docker-compose.yml`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docker-compose.yml)
  Added backend healthcheck against `/api/system/status`.
- [`docker-compose.tilt.yml`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docker-compose.tilt.yml)
  Added dedicated Tilt compose file with backend healthcheck and no bind mount.
- [`Tiltfile`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/Tiltfile)
  Explicitly binds Tilt to `docker-compose.tilt.yml` and live-syncs `backend/`.

### Admin-app

- [`admin-app/src/lib/config.js`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/config.js)
  Unified base URL resolution:
  `VITE_API_BASE_URL` -> `VITE_BACKEND_BASE_URL` -> `window.__APP_CONFIG__` -> `http://cybeer-hub:8000`
- [`admin-app/src/lib/api.js`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/api.js)
  Removed hardcoded `localhost` and now uses shared config.
- [`admin-app/src/App.svelte`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/App.svelte)
  Initializes Tauri backend URL bridge on startup before polling/fetches.
- [`admin-app/src/routes/Login.svelte`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Login.svelte)
  Uses the shared config and initializes Tauri bridge before login.
- [`admin-app/src/routes/Dashboard.svelte`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Dashboard.svelte)
  Shows current API base URL in dev mode or when `VITE_SHOW_API_BASE_URL=true`.
- [`admin-app/src-tauri/src/api_client.rs`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/src/api_client.rs)
  Replaced hardcoded localhost API URL with runtime-configurable backend base URL.
- [`admin-app/src-tauri/src/main.rs`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/src/main.rs)
  Added `configure_backend_base_url` Tauri command and startup log.

### Controller

- [`rpi-controller/config.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/rpi-controller/config.py)
  Default backend target now is `http://cybeer-hub:8000`.
- [`rpi-controller/main.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/rpi-controller/main.py)
  Logs config and runs backend startup probe on boot.
- [`rpi-controller/sync_manager.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/rpi-controller/sync_manager.py)
  Logs backend URL, resolved IPs, startup probe result, and includes URL in network error logs.

## 4. How to run

Detailed runbook: [`docs/dev/TILT_RUNBOOK.md`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docs/dev/TILT_RUNBOOK.md)

Short version:

```bash
tilt up
```

Environment expected on `cybeer-hub`:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `DATABASE_URL=postgresql://<user>:<password>@postgres:5432/<db>`
- `SECRET_KEY`
- `INTERNAL_API_KEY`
- `INTERNAL_TOKEN`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALLOW_LEGACY_DEMO_INTERNAL_TOKEN`

Optional frontend env on developer host:

- `VITE_API_BASE_URL=http://cybeer-hub:8000`
- `VITE_SHOW_API_BASE_URL=true`

`/etc/hosts`:

- Not needed inside Docker containers.
- Needed on dev hosts and RPis only if `cybeer-hub` is not resolvable via DNS or mDNS.

Open ports:

- `8000/tcp` from dev hosts and RPis to `cybeer-hub`
- `5173/tcp` only for shared Vite dev usage
- `5432/tcp` only if host-side DB access is intentionally required

## 5. How to verify

- Backend env: `docker exec beer_backend_api python -c "import os; print(os.environ['DATABASE_URL'])"`
- DB revision: `docker exec beer_backend_api python -m alembic current`
- Migrations: `docker exec beer_backend_api python -m alembic upgrade head`
- Backend root: `curl -fsS http://cybeer-hub:8000/`
- Backend DB-backed status: `curl -fsS http://cybeer-hub:8000/api/system/status`
- Admin-app web: confirm browser network hits `cybeer-hub`, not `localhost`
- Admin-app Tauri: confirm Tauri log prints backend base URL `http://cybeer-hub:8000`
- Controller: confirm startup log prints `SERVER_URL=http://cybeer-hub:8000`, resolved IPs, and probe `200`
- Backend logs: confirm requests from controller appear on `/api/system/status`, `/api/visits/authorize-pour`, `/api/sync/pours`

## 6. Non-goals / Known limitations

- Pure browser mode of admin-app still relies mainly on the existing Tauri-command architecture; this change focused on removing `localhost` and unifying the configured backend target, not on converting all app flows to raw browser HTTP.
- Local Docker verification on this Windows workstation hit an environment-specific issue where `postgres:15-alpine` remained stuck in `initdb` and never reached healthy state. Backend/Tilt config changes were still applied, but full container smoke could not be completed here because Postgres did not finish initializing.
- Local `npm ci` was blocked by a Windows `EPERM` lock on `admin-app/node_modules/@rollup/rollup-win32-x64-msvc/rollup.win32-x64-msvc.node`; `cargo check` for Tauri and Python compilation checks still completed successfully.
