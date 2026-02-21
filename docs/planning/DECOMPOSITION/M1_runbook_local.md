# M1 Local Execution Runbook (Alembic-Only Schema Path)

## Scope
- Purpose: local/dev verification of M1 migration baseline with Alembic as the single schema writer.
- Assumption: `Base.metadata.create_all()` is removed/disabled in M1 runtime path.

## Prerequisites
1. Docker + Docker Compose available.
2. Repo cloned and `.env` configured with at least:
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_DB`
   - `DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}`

---

## 1) Clean DB Bootstrap (from empty volume)

### 1.1 Stop stack and remove old Postgres volume
```bash
docker-compose down -v
````

### 1.2 Start only Postgres and wait until healthy

```bash
docker-compose up -d postgres
```

```bash
docker-compose ps
```

### 1.3 Apply migrations BEFORE starting backend

```bash
docker-compose run --rm beer_backend_api alembic upgrade head
```

### 1.4 Start backend API

```bash
docker-compose up -d beer_backend_api
```

### 1.5 Verify Alembic revision state

```bash
docker-compose exec beer_backend_api alembic current
```

```bash
docker-compose exec beer_backend_api alembic history
```

---

## 2) Start Backend and Verify Health

### 2.1 Ensure backend is running
```bash
docker-compose ps
```

### 2.2 Check service health endpoint
```bash
curl -fsS http://localhost:8000/
```

Expected response includes:
- `Beer Tap System Backend is running!`

### 2.3 Optional docs endpoint check
```bash
curl -fsS http://localhost:8000/docs > /dev/null && echo "Swagger OK"
```

---

## 3) Apply New Migrations (standard dev workflow)

### 3.1 Create a revision (example)
```bash
docker-compose exec beer_backend_api alembic revision -m "m1_example_additive_change"
```

### 3.2 Apply revision
```bash
docker-compose exec beer_backend_api alembic upgrade head
```

### 3.3 Confirm current revision
```bash
docker-compose exec beer_backend_api alembic current
```

---

## 4) Minimal Downgrade Capability Check (one-time)

> M1 requirement: one minimal downgrade/upgrade cycle only.

### 4.1 Capture current revision
```bash
docker-compose exec beer_backend_api alembic current
```

### 4.2 Downgrade one step
```bash
docker-compose exec beer_backend_api alembic downgrade -1
```

### 4.3 Re-upgrade to head
```bash
docker-compose exec beer_backend_api alembic upgrade head
```

### 4.4 Re-check backend health
```bash
curl -fsS http://localhost:8000/
```

Acceptance:
- `downgrade -1` succeeds once on latest/simple revision.
- `upgrade head` succeeds afterward.
- backend health endpoint remains reachable.

---

## 5) Troubleshooting Quick Checks

### 5.1 Migration command fails due to DB connection
```bash
docker-compose logs postgres --tail=100
```

```bash
docker-compose logs beer_backend_api --tail=100
```

### 5.2 Verify environment inside backend container
```bash
docker-compose exec beer_backend_api env | grep -E "POSTGRES_|DATABASE_URL"
```

### 5.3 Validate tables exist after migration
```bash
docker-compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"
```
