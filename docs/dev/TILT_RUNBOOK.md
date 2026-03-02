# Tilt Runbook

## Host assumptions

- `cybeer-hub` is the Linux host running Docker and Tilt.
- `cybeer-hub` must resolve from developer workstations and from each RPi controller.
- Backend is published on `http://cybeer-hub:8000`.
- Postgres stays internal to Docker and is reached by backend at `postgres:5432`.

## Required environment

Create a root `.env` on `cybeer-hub` with:

```env
POSTGRES_USER=beer_user
POSTGRES_PASSWORD=beer_password
POSTGRES_DB=beer_tap_db
DATABASE_URL=postgresql://beer_user:beer_password@postgres:5432/beer_tap_db
SECRET_KEY=replace-with-a-long-random-secret
INTERNAL_API_KEY=replace-with-internal-service-token
INTERNAL_TOKEN=replace-with-internal-service-token
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOW_LEGACY_DEMO_INTERNAL_TOKEN=true
```

Optional frontend override:

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
```

## Name resolution

- Preferred: local DNS or mDNS/Avahi resolves `cybeer-hub`.
- Fallback: add `cybeer-hub` to `/etc/hosts` on developer hosts and RPis.
- Docker containers do not need `/etc/hosts` for `cybeer-hub`; backend talks to Postgres via the Docker service name `postgres`.

## Open ports

- `8000/tcp` from developer hosts and RPis to `cybeer-hub`
- `5173/tcp` only if you expose Vite dev server to other machines
- `5432/tcp` only if you intentionally need host access to Postgres; backend itself does not require this externally

## Start

On `cybeer-hub`:

```bash
docker compose -f docker-compose.yml down
tilt up
```

Tilt uses [`docker-compose.tilt.yml`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docker-compose.tilt.yml) via [`Tiltfile`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/Tiltfile).

## Verify backend and DB

```bash
docker exec beer_backend_api python -c "import os; print(os.environ['DATABASE_URL'])"
docker exec beer_backend_api python -m alembic current
docker exec beer_backend_api python -m alembic upgrade head
docker exec beer_backend_api python -m alembic heads
curl -fsS http://cybeer-hub:8000/
curl -fsS http://cybeer-hub:8000/api/system/status
docker logs beer_backend_api --tail 200
```

Expected:

- `DATABASE_URL` points to `postgres:5432`
- `alembic current` matches `alembic heads`
- `/` returns `200`
- `/api/system/status` returns `200`

## Verify admin-app

Web dev:

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
npm run dev
```

Expected:

- Browser console logs `API_BASE_URL=http://cybeer-hub:8000`
- Dashboard shows `API base URL: http://cybeer-hub:8000` in dev mode
- Browser network requests for login go to `cybeer-hub`, not `localhost`

Tauri:

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
npm run tauri dev
```

Expected:

- Tauri log prints `[CONFIG] backend base url = http://cybeer-hub:8000`
- Tauri commands reach backend on `cybeer-hub`

## Verify controller

On the RPi:

```bash
getent hosts cybeer-hub || nslookup cybeer-hub
curl -fsS http://cybeer-hub:8000/
curl -fsS http://cybeer-hub:8000/api/system/status
journalctl -u beer-controller -n 100 --no-pager
```

Expected controller logs:

- `Controller backend config: SERVER_URL=http://cybeer-hub:8000 ...`
- `RESOLVED_IPS=...`
- `Backend startup probe OK: url=http://cybeer-hub:8000/api/system/status status_code=200`

## Smoke checklist

- Backend container becomes healthy only after DB schema reaches Alembic head.
- Backend logs show controller requests on `/api/system/status`, `/api/visits/authorize-pour`, and `/api/sync/pours`.
- No active code path in `admin-app/src`, `admin-app/src-tauri/src`, `backend`, or `rpi-controller` still targets `localhost:8000`.
