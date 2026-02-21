# M1 — Migration Baseline Decomposition

## A) Current State Summary

### Backend stack (source-of-truth from repository)
- **Language/framework:** Python 3.11 + FastAPI (`backend/main.py`, `backend/Dockerfile`, `backend/requirements.txt`).
- **ORM:** SQLAlchemy declarative ORM (`backend/database.py`, `backend/models.py`).
- **Migration tool:** Alembic is installed/configured (`backend/alembic.ini`, `backend/alembic/env.py`) but migration history is not yet established in `backend/alembic/versions/`.

### Databases and environment usage
- **Backend DB:** PostgreSQL (Docker `postgres` service, backend uses `DATABASE_URL`).
- **Controller DB:** Local SQLite WAL journal in `rpi-controller/database.py` (out of M1 scope).

### How DB is initialized today
- Backend currently runs `models.Base.metadata.create_all(bind=engine)` at startup (`backend/main.py`).
- Alembic helper script exists (`init-db.sh`), but without baseline history this is not yet the enforced schema path.

### Where core pieces live
- Models: `backend/models.py`
- DB engine/session/base: `backend/database.py`
- App startup: `backend/main.py`
- Migration config/scripts: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/`
- Infra/env wiring: `docker-compose.yml`, `README.md`

---

## B) Proposed Migration Strategy

### Confirmed M1 decisions
1. **`Base.metadata.create_all()` will be removed/disabled in M1.**
2. **Alembic becomes the single schema writer from M1 onward.**
3. **Downgrade drill remains minimal:** one-time verification on a simple/latest revision only.

### Minimal baseline approach
1. Create initial Alembic baseline revision for current backend schema.
2. For clean DB: `alembic upgrade head` is the only schema bootstrap path.
3. For existing DB with matching schema: `alembic stamp <baseline_rev>` then `alembic upgrade head`.
4. If schema mismatch is found, reconcile before stamp; do not stamp blindly.

### Existing schema/data safety
- No destructive migration operations in M1 baseline.
- Use backup-first procedure for pilot/staging before any migration run.
- Keep controller SQLite schema initialization unchanged in M1.

### Multiple environments
- **Dev docker:** `.env` + `docker-compose` (`POSTGRES_*`, `DATABASE_URL`).
- **Pilot:** same commands with controlled maintenance window + verified backup.
- **CI/local checks:** clean upgrade smoke + one minimal downgrade capability check.

---

## C) Task Breakdown (M1)

> Legend: **[CP]** critical path.

1. **M1-01 [CP] — Confirm scope boundary**
   - Description: Backend Postgres only; controller SQLite explicitly excluded.
   - Paths: `backend/`, `rpi-controller/`, `docs/planning/PIPELINE_V1/07_demo_oriented_pipeline.md`
   - Acceptance: Boundary recorded in M1 docs.
   - Risk: Scope creep.

2. **M1-02 [CP] — Inventory schema entry points**
   - Description: Identify all schema creation paths and deprecate non-migration paths.
   - Paths: `backend/main.py`, `backend/alembic/*`, `init-db.sh`
   - Acceptance: Alembic designated as sole writer in docs.
   - Risk: Hidden initializer remains.

3. **M1-03 [CP] — Define migration policy (additive-first)**
   - Description: Document allowed/forbidden migration types for pilot phase.
   - Paths: `docs/planning/DECOMPOSITION/M1_migration_baseline.md`
   - Acceptance: No-drop/no-rename default documented.
   - Risk: Unsafe migration scripts.

4. **M1-04 [CP] — Align env contract for Alembic/app**
   - Description: Document exact env variable usage and command context.
   - Paths: `backend/alembic/env.py`, `backend/database.py`, `README.md`
   - Acceptance: Commands run consistently in docker and local shell.
   - Risk: Env mismatch failures.

5. **M1-05 [CP] — Create baseline revision**
   - Description: Generate and review initial Alembic revision for current schema.
   - Paths: `backend/alembic/versions/*`, `backend/models.py`
   - Acceptance: Baseline revision committed and reviewed.
   - Risk: Baseline drift/incorrect DDL.

6. **M1-06 [CP] — Disable/remove `create_all` in startup**
   - Description: Remove schema auto-create dependency from runtime startup path.
   - Paths: `backend/main.py`
   - Acceptance: App startup does not execute `Base.metadata.create_all()`.
   - Risk: Startup fails if migration step is skipped.

7. **M1-07 [CP] — Validate clean bootstrap**
   - Description: Empty Postgres → `alembic upgrade head` → app start.
   - Paths: `docker-compose.yml`, `backend/alembic/*`, `init-db.sh`
   - Acceptance: Clean DB fully bootstraps via migrations only.
   - Risk: Residual dependency on old initializer.

8. **M1-08 [CP] — Validate existing DB onboarding**
   - Description: Snapshot parity check + stamp + upgrade path.
   - Paths: `backend/alembic/*`, `docs/planning/DECOMPOSITION/M1_checklist.md`
   - Acceptance: Existing DB path validated with no data loss.
   - Risk: False-safe stamping.

9. **M1-09 — Document developer workflow**
   - Description: Create/apply/history/current commands plus review expectations.
   - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`
   - Acceptance: New dev can execute flow without tribal knowledge.
   - Risk: Workflow bypass.

10. **M1-10 — Add migration PR checklist**
    - Description: Require manual review for generated migrations.
    - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`
    - Acceptance: Checklist includes additive/data-safety checks.
    - Risk: Low-quality migration scripts.

11. **M1-11 [CP] — Pilot backup + recovery note**
    - Description: Define backup-first and recovery decision process.
    - Paths: `docs/planning/DECOMPOSITION/M1_risks.md`
    - Acceptance: Recovery path documented and reviewed.
    - Risk: Pilot downtime.

12. **M1-12 [CP] — Minimal downgrade drill (one-time)**
    - Description: Verify one downgrade/upgrade cycle on simple latest revision only.
    - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`
    - Acceptance: One successful downgrade capability check recorded.
    - Risk: Over-expanding rollback scope.

13. **M1-13 [CP] — Freeze manual DDL outside migrations**
    - Description: Disallow direct schema edits except emergency recovery.
    - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`, `M1_risks.md`
    - Acceptance: Policy documented and accepted.
    - Risk: Schema drift.

14. **M1-14 [CP] — Assign migration execution ownership**
    - Description: Define author/reviewer/operator roles.
    - Paths: `docs/planning/DECOMPOSITION/M1_risks.md`
    - Acceptance: Ownership matrix complete.
    - Risk: Unclear accountability.

15. **M1-15 [CP] — Final DoD review**
    - Description: Validate all M1 acceptance criteria and evidence.
    - Paths: all three M1 docs
    - Acceptance: Signed DoD checklist.
    - Risk: Carrying baseline risk into M2.

### Critical path
**M1-01 → M1-02 → M1-03 → M1-04 → M1-05 → M1-06 → M1-07 + M1-08 → M1-11 → M1-12 → M1-15**

---

## D) Acceptance Criteria / Definition of Done

M1 is complete only when all are true:
1. Baseline migration history exists in `backend/alembic/versions/` and lineage is consistent.
2. **`Base.metadata.create_all()` is removed/disabled from runtime startup.**
3. New developer can run documented commands, apply migrations, and start API on a clean DB.
4. Existing DB onboarding path is validated (`parity check + stamp + upgrade`) or a tested equivalent is documented.
5. Alembic is explicitly documented as the single schema writer.
6. Migration workflow (create/review/apply) is documented and repeatable.
7. **One minimal downgrade capability check is executed and recorded** (single latest/simple revision), without requiring a full downgrade runbook expansion.
8. Backup-first safety and recovery note are documented for pilot execution.

---

## Smoke Test Plan

### 1) Clean DB bootstrap
1. Start empty Postgres.
2. Run `alembic upgrade head`.
3. Start backend API.
4. Verify health/core endpoint response.

Expected: schema created by migrations only; app starts without `create_all`.

### 2) Existing DB snapshot onboarding
1. Restore representative snapshot.
2. Check schema parity vs baseline.
3. Run `alembic stamp <baseline_rev>` if parity is confirmed.
4. Run `alembic upgrade head`.
5. Verify data + basic API read/write.

Expected: no data loss; DB tracked at head.

### 3) Minimal downgrade capability check
1. On a simple latest revision, run one-step downgrade.
2. Re-run upgrade to head.

Expected: one successful downgrade/upgrade cycle is recorded.

---

## E) Safety / Rollback Plan

### Pre-deploy safety gates
- Mandatory backup before migration execution.
- Rehearsal on staging/snapshot.
- Controlled execution window and designated operator.

### If migration baseline fails in pilot environment
1. Pause writes.
2. Capture migration error/revision context.
3. If the one-step tested downgrade is clearly applicable, use it.
4. Otherwise restore from pre-migration backup.
5. Validate service health and core flows.
6. Re-attempt only after staging re-validation.

### Rollback scope note
- M1 keeps rollback lightweight by design: one verified downgrade capability check + backup-restore fallback; no expanded full downgrade playbook in this milestone.

---

## Implementation Options

### Option A — Minimal baseline (**Recommended**)
- Baseline revision + existing DB stamp path.
- Remove/disable `create_all` in M1.
- Migrations-only bootstrap and one minimal downgrade capability check.

Pros: fastest, safest for demo/pilot; enforces single schema writer now.

### Option B — Fuller baseline
- Option A plus stricter CI automation and broader migration governance hardening in same milestone.

Pros: stronger discipline; Cons: slower and higher coordination overhead.

### Recommendation
Use **Option A** now for pilot readiness and investor continuity, then schedule Option B hardening immediately after M1.
