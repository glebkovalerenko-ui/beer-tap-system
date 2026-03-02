# Tilt Runbook

## 1. Start Tilt

Use one orchestrator at a time. On `cybeer-hub`, stop the legacy compose stack before starting Tilt:

```powershell
docker compose -f docker-compose.yml down
tilt up
tilt get uiresources
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

Expected:

- `beer_backend_api` and `beer_postgres_db` are the only backend/DB containers.
- `beer_backend_api` exposes `8000/tcp`.
- `beer_postgres_db` exposes `5432/tcp`.

## 2. Check Database

```powershell
docker exec beer_backend_api sh -lc "printenv | grep DATABASE_URL"
docker exec beer_backend_api sh -lc "python -m alembic current -v"
docker exec beer_backend_api sh -lc "python -m alembic heads"
docker exec beer_backend_api sh -lc "getent hosts postgres"
docker exec beer_postgres_db psql -U beer_user -d beer_tap_db -c "select version_num from alembic_version;"
```

Expected:

- `DATABASE_URL` points to `postgres:5432`.
- `alembic current` matches `alembic heads`.
- `postgres` resolves inside the backend container.

## 3. Check Backend

From the Windows workstation:

```powershell
Resolve-DnsName cybeer-hub
Test-NetConnection cybeer-hub -Port 8000
curl.exe -fsS http://cybeer-hub:8000/
curl.exe -fsS http://cybeer-hub:8000/api/system/status
docker logs beer_backend_api --tail 200
```

Expected:

- DNS resolves `cybeer-hub`.
- TCP `8000` is reachable.
- `/` returns `200`.
- `/api/system/status` returns `200` and does not fail with missing-table errors.

## 4. Check Controller

On the controller:

```bash
getent hosts cybeer-hub || nslookup cybeer-hub
curl -v http://cybeer-hub:8000/
curl -v http://cybeer-hub:8000/api/system/status
journalctl -u beer-controller -n 100 --no-pager
```

Expected controller logs:

- `Controller backend config: SERVER_URL=http://cybeer-hub:8000`
- `Backend startup probe OK: url=http://cybeer-hub:8000/api/system/status status_code=200`

## 5. Check Admin App

Set the frontend source of truth before starting Vite/Tauri:

```powershell
$env:VITE_BACKEND_BASE_URL="http://cybeer-hub:8000"
npm run dev
```

Quick checks:

```powershell
git grep -n localhost -- admin-app/src admin-app/src-tauri/src rpi-controller backend ':!backend/alembic.ini'
```

Expected:

- Browser dev console prints `backend base url = http://cybeer-hub:8000` once on startup.
- Tauri logs print `[CONFIG] backend base url = http://cybeer-hub:8000`.
- Critical app paths do not contain backend fallbacks to `localhost`.
