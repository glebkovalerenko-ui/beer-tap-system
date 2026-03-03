# Syncthing Migration Plan

## A. Current diagnostics

### Linux host snapshot

- Host: `cybeer-hub`
- Kernel: `Linux cybeer-hub 6.12.47+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.12.47-1+rpt1 (2025-09-16) aarch64 GNU/Linux`
- OS: `Debian GNU/Linux 13 (trixie)`
- Docker server: `29.2.1`
- Docker Compose: `v5.1.0`
- Listening ports during capture: `22`, `5432`, `8000`
- Hostname resolution on Linux: `getent hosts cybeer-hub` -> `127.0.1.1 cybeer-hub`
- Primary host IP: `eth0 192.168.0.110/24`

### Running containers

At capture time:

- `beer_backend_api` -> `beer_backend_api`, status `Up 26 hours (healthy)`, published `8000:8000`
- `beer_postgres_db` -> `postgres:15-alpine`, status `Up 26 hours (healthy)`, published `5432:5432`

### Compose and Tilt facts

- No project checkout was found under `/home/cybeer` or `/srv` on Linux during the initial scan.
- Running backend container labels show it was created from `docker-compose.tilt.yml`.
- Running backend container labels also include `dev.tilt.*`, confirming the active workflow still depends on Tilt.
- Backend container has no bind mounts.
- Postgres uses named volume `beer-tap-system_postgres_data` mounted to `/var/lib/postgresql/data`.

### Backend and DB facts

- Backend env contains `DATABASE_URL=postgresql://beer_user:beer_password@postgres:5432/beer_tap_db`.
- Backend entrypoint runs `python -m alembic upgrade head` before `uvicorn`.
- Alembic state in the running container: current revision `0012_m6_rejected_sync`, head `0012_m6_rejected_sync`.
- Postgres health was `healthy`; health probe output: `/var/run/postgresql:5432 - accepting connections`.
- Backend health was `healthy`.
- `curl http://localhost:8000/` on Linux returned `{"Status":"Beer Tap System Backend is running!"}`.
- `curl http://localhost:8000/api/system/status` on Linux returned HTTP `200` with `{"key":"emergency_stop_enabled","value":"false"}`.
- `docker exec beer_postgres_db psql -U beer_user -d beer_tap_db -c 'SELECT 1;'` succeeded.
- `docker exec beer_backend_api getent hosts postgres` returned `172.18.0.2 postgres`.

### Root cause summary

- Database connectivity is working now; the earlier "backend does not see DB" symptom is not reproducible in the current Linux state.
- The real dev-workflow gap is elsewhere: backend code on Linux currently comes from a baked image created by Tilt, not from a stable synced checkout.
- That means Windows edits do not become the live backend source of truth unless Tilt performs its own sync/rebuild path.

### Admin app URL facts

`grep` across the repo shows:

- `localhost:5173` is present in [`admin-app/src-tauri/tauri.conf.json`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/tauri.conf.json) as Tauri `devUrl` only.
- Active backend defaults are `http://cybeer-hub:8000` in [`admin-app/src/lib/config.js`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/config.js), [`admin-app/src-tauri/src/server_config.rs`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/src/server_config.rs), and [`rpi-controller/config.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/rpi-controller/config.py).
- No active admin-app code path still falls back to `http://localhost:8000`.

## B. Migration plan

### 1. Windows: manual operator steps

1. Install Syncthing or SyncTrayzor on Windows.
2. Share the repo root folder as `Send Only`.
3. Use the repository root [`.stignore`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.stignore).
4. Keep secrets local on each machine; do not sync `.env`, keys, certs, or credentials.
5. Start admin-app locally with `VITE_API_BASE_URL=http://cybeer-hub:8000`.
6. For Tauri dev, keep `devUrl=http://localhost:5173`; that remains frontend-only.

### 2. Linux: automated through SSH

1. Create stable repo path `/home/cybeer/beer-tap-system`.
2. Install Syncthing and run it as a `systemd --user` service for `cybeer`.
3. Enable linger so the user service survives logout.
4. Pre-create the Linux repo directory as the Syncthing `Receive Only` target.
5. Keep `.env` local on Linux and run `docker compose` from `/home/cybeer/beer-tap-system`.
6. Use the existing named postgres volume; do not remove it.
7. Use the simplest pilot reload path: bind-mounted backend source plus `uvicorn --reload` inside the container.
8. Keep existing healthchecks and DB readiness gating via `depends_on: condition: service_healthy`.

### 3. Controller: minimal changes

1. Confirm `SERVER_URL=http://cybeer-hub:8000` on the controller.
2. Confirm `INTERNAL_TOKEN` or `INTERNAL_API_KEY` matches backend expectations.
3. Restart the controller process after any URL/token change.
4. Watch controller logs for resolved host/IP output from `sync_manager.py`.

### 4. End-to-end verification

1. Edit a backend file on Windows.
2. Verify Syncthing delivers it into `/home/cybeer/beer-tap-system/backend`.
3. Verify `uvicorn --reload` restarts backend automatically.
4. Call `curl http://localhost:8000/api/system/status` on Linux.
5. Start admin-app on Windows with `VITE_API_BASE_URL=http://cybeer-hub:8000` and verify login/API calls.
6. Trigger a controller sync and verify backend access logs show the request.

## C. Changes made

### Repository changes

- Removed [`Tiltfile`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/Tiltfile).
- Removed [`docker-compose.tilt.yml`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docker-compose.tilt.yml).
- Removed [`docs/dev/TILT_RUNBOOK.md`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docs/dev/TILT_RUNBOOK.md).
- Added root Syncthing ignore file [`.stignore`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.stignore).
- Added Syncthing runbook [`docs/dev/SYNCTHING_DEV_RUNBOOK.md`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docs/dev/SYNCTHING_DEV_RUNBOOK.md).
- Added admin-app URL memo [`docs/dev/ADMIN_APP_BACKEND_URL.md`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docs/dev/ADMIN_APP_BACKEND_URL.md).
- Updated [`docs/INDEX.md`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docs/INDEX.md).
- Updated [`.gitignore`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.gitignore) for Syncthing artifacts.

### Linux changes

See the final section of this report after execution for exact commands and outcomes.

## D. Admin app: localhost clarification

### Repo grep conclusion

- `localhost:5173` in Tauri config is the frontend dev server for Tauri shell startup.
- Backend URL selection in web/dev is centralized in [`admin-app/src/lib/config.js`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/config.js).
- Tauri runtime persistence is centralized in [`admin-app/src-tauri/src/server_config.rs`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/src/server_config.rs).
- There is no active hidden fallback to `localhost:8000`.

### Practical rule

- Web/dev: set `VITE_API_BASE_URL=http://cybeer-hub:8000`
- Tauri desktop: use the persisted runtime server setting, default `http://cybeer-hub:8000`
- Tauri `devUrl`: leave `http://localhost:5173`; it does not change backend target

## E. Controller visibility in backend logs

### Controller checklist

1. Check controller config: `SERVER_URL=http://cybeer-hub:8000`
2. Check token config: `INTERNAL_TOKEN` or `INTERNAL_API_KEY`
3. From the controller host, resolve `cybeer-hub` and verify it points to `192.168.0.110`
4. Run a direct probe to backend from the controller host
5. Restart controller and inspect startup log line with resolved host/IPs

### What to watch on Linux

- Backend access logs:

```bash
cd /home/cybeer/beer-tap-system
docker compose logs -f beer_backend_api
```

- Live request probe:

```bash
curl -fsS http://localhost:8000/api/system/status
```

If controller traffic still does not appear, inspect the controller host first. A reverse proxy is not required for this pilot because backend already publishes `8000/tcp` directly and access logs are visible from uvicorn.

## Linux execution log

### Status

- Pending in the first draft of this file; updated after Linux execution.

## Runbook

### Start

```bash
cd /home/cybeer/beer-tap-system
docker compose up -d --build
```

### Stop

```bash
cd /home/cybeer/beer-tap-system
docker compose stop
```

### Logs

```bash
cd /home/cybeer/beer-tap-system
docker compose logs -f beer_backend_api
docker compose logs -f postgres
```

### Smoke checks

```bash
cd /home/cybeer/beer-tap-system
curl -fsS http://localhost:8000/
curl -fsS http://localhost:8000/api/system/status
docker compose exec beer_postgres_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SELECT 1;'
docker compose exec beer_backend_api python -m alembic current
```

## Known issues

- Syncthing pairing with the Windows workstation still requires the Windows device ID and folder acceptance on both sides.
- Historical docs in `docs/reports/` and some older planning files still mention Tilt or `localhost`; they are preserved as historical material, not active runbooks.

## Rollback

1. Stop the compose stack from `/home/cybeer/beer-tap-system`.
2. Re-run the old image-based stack only if you intentionally want to return to the previous Tilt-driven flow.
3. Do not remove `beer-tap-system_postgres_data`.
4. Disable Syncthing user service if needed: `systemctl --user disable --now syncthing`.
