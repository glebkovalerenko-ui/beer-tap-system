# Syncthing Dev Runbook

## Target topology

- Windows workstation: edit code locally and run `admin-app`.
- Linux host `cybeer-hub`: run Docker containers for `beer_backend_api` and `beer_postgres_db`.
- Syncthing: Windows folder is `Send Only`, Linux folder is `Receive Only`.

## Stable Linux path

Use `/home/cybeer/beer-tap-system` as the only dev checkout on Linux.

`docker compose` must always run from that directory so `./backend:/app` resolves to synced code.

## Syncthing folder settings

- Folder path: repo root on both machines.
- Folder type on Windows: `Send Only`.
- Folder type on Linux: `Receive Only`.
- Ignore file: root [`.stignore`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.stignore).
- Do not sync secrets: `.env`, `.env.*`, keys, certs, local caches, build output.

## Linux start

```bash
cd /home/cybeer/beer-tap-system
cp .env.example .env   # only once, then edit values locally on Linux
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

## Reload model

- Backend code is bind-mounted from `/home/cybeer/beer-tap-system/backend`.
- `uvicorn --reload` inside the container is the pilot auto-reload mechanism.
- Schema changes still require container restart if dependency state changes materially.

## Diagnostics

```bash
cd /home/cybeer/beer-tap-system
docker compose ps
docker compose logs -f beer_backend_api
docker compose logs -f postgres
docker compose exec beer_backend_api python -m alembic current
docker compose exec beer_postgres_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SELECT 1;'
curl -fsS http://localhost:8000/
curl -fsS http://localhost:8000/api/system/status
```

## Notes

- Do not run `docker compose down -v` unless you intentionally want to destroy PostgreSQL data.
- If Syncthing reports local additions on Linux, prefer `Revert Local Changes` because Linux is `Receive Only`.
