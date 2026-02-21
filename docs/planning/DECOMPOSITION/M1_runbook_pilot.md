# M1 Pilot Execution Runbook (Safe Cutover)

## Scope
- Purpose: safely onboard existing pilot DB to Alembic baseline and upgrade to head.
- Decision alignment:
  - Alembic is the single schema writer.
  - `create_all` is removed/disabled in M1 runtime.
  - Rollback posture is backup-restore first; minimal downgrade remains optional and limited.

## Variables (set before running)
```bash
export TS=$(date +%Y%m%d_%H%M%S)
export DB_NAME="${POSTGRES_DB}"
export DB_USER="${POSTGRES_USER}"
export BASELINE_REV="<put_baseline_revision_id_here>"
export BACKUP_FILE="/tmp/${DB_NAME}_${TS}.dump"
export SCHEMA_FILE="/tmp/${DB_NAME}_${TS}_schema.sql"
export SCRATCH_DB="${DB_NAME}_m1_scratch_${TS}"
```

---

## 1) Maintenance Window Checklist
- [ ] Maintenance window announced and approved.
- [ ] Writes paused (admin/operator informed).
- [ ] Migration operator and reviewer both present.
- [ ] Backup storage path confirmed with enough free space.
- [ ] Rollback owner assigned.

---

## 2) Backup Step (mandatory)

## 2.1 Full logical backup (data + schema)
```bash
docker-compose exec postgres pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -f "$BACKUP_FILE"
```

## 2.2 Export schema-only snapshot (audit/reference)
```bash
docker-compose exec postgres pg_dump -U "$DB_USER" -d "$DB_NAME" --schema-only -f "$SCHEMA_FILE"
```

## 2.3 Verify backup artifact exists
```bash
docker-compose exec postgres ls -lh "$BACKUP_FILE" "$SCHEMA_FILE"
```

---

## 3) Schema Parity Check (single concrete method)

### Method chosen
**Dry-run on scratch clone restored from pilot backup** before touching real DB.

### 3.1 Create scratch DB from backup
```bash
docker-compose exec postgres createdb -U "$DB_USER" "$SCRATCH_DB"
```

```bash
docker-compose exec postgres pg_restore -U "$DB_USER" -d "$SCRATCH_DB" "$BACKUP_FILE"
```

### 3.2 Run baseline onboarding flow on scratch DB
> Run Alembic against scratch DB by overriding `POSTGRES_DB` for command scope.

```bash
docker-compose exec -e POSTGRES_DB="$SCRATCH_DB" beer_backend_api alembic stamp "$BASELINE_REV"
```

```bash
docker-compose exec -e POSTGRES_DB="$SCRATCH_DB" beer_backend_api alembic upgrade head
```

### 3.3 Validate revision state on scratch DB
```bash
docker-compose exec -e POSTGRES_DB="$SCRATCH_DB" beer_backend_api alembic current
```

Pass condition:
- Scratch stamp + upgrade completes successfully without schema/data errors.

---

## 4) Production Pilot Stamp + Upgrade Sequence

## 4.1 Stamp baseline on real pilot DB (only after scratch pass)
```bash
docker-compose exec beer_backend_api alembic stamp "$BASELINE_REV"
```

## 4.2 Upgrade to head
```bash
docker-compose exec beer_backend_api alembic upgrade head
```

## 4.3 Verify current revision
```bash
docker-compose exec beer_backend_api alembic current
```

---

## 5) Post-Migration Validation

## 5.1 Backend process check
```bash
docker-compose ps
```

## 5.2 API health checks
```bash
curl -fsS http://localhost:8000/
```

```bash
curl -fsS http://localhost:8000/docs > /dev/null && echo "Swagger OK"
```

## 5.3 DB object check
```bash
docker-compose exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "\dt"
```

## 5.4 Record migration evidence
- Save command outputs for:
  - backup file listing
  - scratch validation (`stamp`, `upgrade`, `current`)
  - production `current`
  - API health response

---

## 6) Rollback: Restore from Backup (primary recovery path)

> Use when pilot DB migration fails or post-checks are not acceptable.

## 6.1 Pause writes and stop backend
```bash
docker-compose stop beer_backend_api
```

## 6.2 Recreate target DB
```bash
docker-compose exec postgres dropdb -U "$DB_USER" --if-exists "$DB_NAME"
```

```bash
docker-compose exec postgres createdb -U "$DB_USER" "$DB_NAME"
```

## 6.3 Restore from backup
```bash
docker-compose exec postgres pg_restore -U "$DB_USER" -d "$DB_NAME" "$BACKUP_FILE"
```

## 6.4 Start backend and verify health
```bash
docker-compose start beer_backend_api
```

```bash
curl -fsS http://localhost:8000/
```

## 6.5 Incident record
- Capture failure command/logs and restoration timestamp.
- Keep system on restored state until corrected migration is re-validated on scratch DB.

---

## 7) Cleanup (optional)

### 7.1 Drop scratch DB after successful cutover
```bash
docker-compose exec postgres dropdb -U "$DB_USER" --if-exists "$SCRATCH_DB"
```
