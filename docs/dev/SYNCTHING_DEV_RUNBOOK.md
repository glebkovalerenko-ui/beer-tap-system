# Syncthing Dev Runbook

Read this after `README.md` and `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`.

## Target topology

- Windows workstation: edit repository and run `admin-app`.
- Linux host `cybeer-hub`: run Docker containers for backend and PostgreSQL.
- Syncthing: Windows checkout is `Send Only`, Linux checkout is `Receive Only`.

## Required Linux path

Use only:

```bash
/home/cybeer/beer-tap-system
```

All backend Docker commands must run from that path so `./backend:/app` points at the synced code.

Retire `/opt/beer-tap-system` on the hub. That stale second checkout is what causes the backend to drift away from the Syncthing-managed tree.

## Syncthing folder settings

- folder path: repository root on both machines
- Windows side: `Send Only`
- Linux side: `Receive Only`
- ignore file: `.stignore`
- do not sync secrets, local caches, or build output
- do not sync runtime backend uploads such as `backend/storage/`; backend media assets must live outside the shared working tree

## Linux start

```bash
cd /home/cybeer/beer-tap-system
cp .env.example .env
docker compose up -d --build
```

## Linux stop

```bash
cd /home/cybeer/beer-tap-system
docker compose stop
```

## Linux restart backend only

```bash
cd /home/cybeer/beer-tap-system
docker compose restart beer_backend_api
```

## Hub auto-apply

The hub should continuously run:

- system service `beer-tap-system.service`
- system timer `beer-tap-sync-reconcile.timer`

The timer calls `beer-tap-sync-reconcile.sh`, waits for Syncthing folder `beer-tap-system-dev` to become `idle`, verifies there are no pull errors or receive-only drift, and then reapplies:

```bash
docker compose up -d --build postgres beer_backend_api
```

Install from the repo copy under `deploy/hub/`.

## Diagnostics

```bash
cd /home/cybeer/beer-tap-system
docker compose ps
docker compose logs -f beer_backend_api
docker compose logs -f postgres
docker compose exec -T beer_backend_api python -m alembic current
curl -fsS http://localhost:8000/
curl -fsS http://localhost:8000/api/system/status
```

## Notes

- backend code is bind-mounted from `/home/cybeer/beer-tap-system/backend`
- backend media assets are stored in Docker volume `backend_media_assets` mounted at `/srv/beer-media-assets`, not inside the synced repo checkout
- `uvicorn --reload` inside the container is the current backend auto-reload mechanism
- if dependency or Dockerfile inputs change, the hub reconcile timer should apply them automatically; manual fallback remains `docker compose up -d --build`
- do not run `docker compose down -v` unless you intentionally want to destroy PostgreSQL data
- if Linux shows local Syncthing drift, prefer `Revert Local Changes` because Linux is the receive-only side
- if Windows is the source of truth, keep SyncTrayzor/Syncthing running on the workstation; a stopped Windows sender means Linux will stay on the last received snapshot
