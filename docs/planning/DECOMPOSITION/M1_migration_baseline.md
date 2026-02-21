# M1 — Migration Baseline Decomposition

## A) Current State Summary

### Backend stack (source-of-truth from repository)
- **Language/framework:** Python 3.11 + FastAPI (`backend/main.py`, `backend/Dockerfile`, `backend/requirements.txt`).
- **ORM:** SQLAlchemy declarative ORM (`backend/database.py`, `backend/models.py`).
- **Migration tool present but not yet baseline-complete:** Alembic is installed and configured (`backend/requirements.txt`, `backend/alembic.ini`, `backend/alembic/env.py`) but there is **no `backend/alembic/versions/` history committed yet**.

### Databases and environment usage
- **Central backend DB (dev/pilot/prod-like): PostgreSQL**
  - Docker service `postgres` (`docker-compose.yml`).
  - Backend connects via `DATABASE_URL` (`backend/database.py`).
  - Alembic currently builds URL from `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_DB` in `env.py` (`backend/alembic/env.py`).
- **Controller local DB (edge/offline): SQLite (WAL mode)**
  - `rpi-controller/database.py` creates local SQLite journal and table `pours` via raw SQL `CREATE TABLE IF NOT EXISTS`.
  - This is separate from backend PostgreSQL schema management and should remain untouched by M1.

### How DB is initialized today
- **Runtime auto-create path is active:** backend executes `models.Base.metadata.create_all(bind=engine)` on application import/start (`backend/main.py`).
- **No migration history gate:** because `create_all` exists and Alembic has no versions baseline, schema can drift from models without tracked revisions.
- **Operational helper script exists:** `init-db.sh` runs `alembic upgrade head` inside backend container, but with no migration versions it cannot provide full historical discipline yet.

### Where schema/model/session/config live
- **Models:** `backend/models.py`
- **Engine/session/base/dependency:** `backend/database.py` (`engine`, `SessionLocal`, `Base`, `get_db`)
- **FastAPI app + current auto-create behavior:** `backend/main.py`
- **Alembic config:** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
- **Infra DB wiring:** `docker-compose.yml`, `.env` pattern documented in `README.md`

---

## B) Proposed Migration Strategy (Minimal, Non-Disruptive)

## Recommended approach for this stack
Because backend already uses SQLAlchemy + Alembic, use **Alembic baseline introduction** (no ORM replacement, no new dependency).

### Baseline principles for M1
1. **Migration tool is the schema source of truth for backend PostgreSQL.**
2. **Additive-first changes only** (no destructive ALTER/DROP in pilot runway).
3. **Single baseline revision first, then incremental revisions.**
4. **Controller SQLite journal remains outside Alembic scope in M1.**

### Handling existing schema without data loss
Use a **baseline + stamp strategy**:
1. Generate baseline revision representing current `backend/models.py` schema.
2. For **new/clean DB**: run `alembic upgrade head` to create schema.
3. For **already-running DBs with matching schema**: use `alembic stamp <baseline_rev>` (or documented equivalent) to register revision **without altering tables/data**.
4. Validate by running a no-op `alembic upgrade head` afterward.
5. If drift exists between live DB and baseline model snapshot, document pre-baseline reconciliation SQL/manual procedure before stamp.

### Handling multiple environments
- **Local docker dev:** env from `.env` + `docker-compose.yml` (`POSTGRES_*`, `DATABASE_URL`).
- **Pilot bar environment:** same migration commands, but controlled execution window + pre-migration DB backup.
- **CI/test environment:** add minimal migration smoke job (upgrade on clean DB + optional downgrade test of latest revision).
- **Controller/RPi environment:** no Alembic changes in M1; keep local SQLite initialization unchanged.

### Minimal changes to runtime behavior (safest)
- Keep startup stability while introducing discipline:
  - Short-term safe path: keep `create_all` until baseline validation is complete, then feature-flag/remove in controlled follow-up task.
  - Preferred near-term endpoint for M1 DoD: startup should not rely on `create_all`; DB should be prepared via migrations.

---

## C) Task Breakdown (M1)

> Legend: **[CP]** = critical path task.

1. **M1-01: Confirm current DB topology and ownership boundaries [CP]**
   - Description: Record backend Postgres vs controller SQLite responsibilities and M1 scope boundary.
   - Paths: `backend/`, `rpi-controller/`, `docs/planning/PIPELINE_V1/07_demo_oriented_pipeline.md`
   - Acceptance: Written boundary section approved in M1 docs.
   - Risk: Scope creep into controller migration work.

2. **M1-02: Inventory backend schema entry points [CP]**
   - Description: Verify all schema creation paths (`create_all`, Alembic, raw SQL scripts).
   - Paths: `backend/main.py`, `backend/alembic/*`, `init-db.sh`, `docs/*.sql`
   - Acceptance: Single source-of-truth table created in docs.
   - Risk: Hidden schema initializer remains active.

3. **M1-03: Define migration policy v1 (additive-first + rollback discipline) [CP]**
   - Description: Document allowed/forbidden migration types for pilot runway.
   - Paths: `docs/planning/DECOMPOSITION/M1_migration_baseline.md`
   - Acceptance: Policy includes no-drop/no-rename default and rollback expectation.
   - Risk: Ambiguous rules causing unsafe revisions.

4. **M1-04: Normalize Alembic environment contract [CP]**
   - Description: Align Alembic connection contract to documented env vars and runtime expectations.
   - Paths: `backend/alembic.ini`, `backend/alembic/env.py`, `README.md`
   - Acceptance: Documented command works consistently in docker and local shell.
   - Risk: Env mismatch (`DATABASE_URL` vs `POSTGRES_*`) causing migration failures.

5. **M1-05: Create initial backend schema baseline revision [CP]**
   - Description: Generate first Alembic revision representing current models (no behavioral changes).
   - Paths: `backend/alembic/versions/*`, `backend/models.py`
   - Acceptance: Baseline revision committed; reproducible on clean DB.
   - Risk: Baseline captures unintended diffs.

6. **M1-06: Validate clean bootstrap from empty Postgres [CP]**
   - Description: Bring up fresh DB and apply `upgrade head` only.
   - Paths: `docker-compose.yml`, `init-db.sh`, `backend/alembic/*`
   - Acceptance: Tables created, app starts, no manual SQL required.
   - Risk: Hidden dependency on `create_all`.

7. **M1-07: Validate existing DB onboarding via stamp procedure [CP]**
   - Description: Test baseline registration on snapshot/simulated existing schema.
   - Paths: `backend/alembic/*`, `docs/planning/DECOMPOSITION/M1_checklist.md`
   - Acceptance: Documented sequence `stamp -> upgrade head` succeeds without data loss.
   - Risk: Stamp on non-matching schema creates false safety.

8. **M1-08: Decide and document `create_all` transition mode [CP]**
   - Description: Choose either temporary compatibility mode or migration-only startup for M1 endpoint.
   - Paths: `backend/main.py`, M1 docs
   - Acceptance: Explicit decision and cutoff date/condition documented.
   - Risk: Dual writers (`create_all` + Alembic) cause drift.

9. **M1-09: Define developer daily workflow**
   - Description: Minimal command cookbook: create revision, review, apply, rollback.
   - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`
   - Acceptance: New developer can follow steps without tribal knowledge.
   - Risk: Team bypasses migration flow under time pressure.

10. **M1-10: Add migration review checklist to PR routine**
    - Description: Require migration script review criteria (idempotency, defaults, data safety).
    - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`
    - Acceptance: Checklist includes mandatory review items.
    - Risk: Low-quality autogenerated migrations merged.

11. **M1-11: Pilot backup + rollback runbook [CP]**
    - Description: Define before/after commands for DB backup, upgrade, rollback, restore.
    - Paths: `docs/planning/DECOMPOSITION/M1_risks.md`
    - Acceptance: Runbook tested in staging-like environment.
    - Risk: Recovery delay during pilot service window.

12. **M1-12: Add migration smoke test recipe [CP]**
    - Description: Add reproducible smoke scenarios for clean DB and existing DB.
    - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`
    - Acceptance: Commands and expected outputs documented.
    - Risk: Unverified process before pilot.

13. **M1-13: Establish ownership and release gate for schema changes [CP]**
    - Description: Define who can approve migration PRs and when they can be deployed.
    - Paths: M1 docs set
    - Acceptance: Approval matrix recorded.
    - Risk: Uncontrolled schema change timing.

14. **M1-14: Freeze manual schema edits outside migration scripts [CP]**
    - Description: Explicitly forbid direct psql DDL except emergency runbook.
    - Paths: `docs/planning/DECOMPOSITION/M1_checklist.md`, `M1_risks.md`
    - Acceptance: Policy published and acknowledged.
    - Risk: Out-of-band drift.

15. **M1-15: Exit review for M1 Definition of Done [CP]**
    - Description: Validate all DoD criteria with artifacts/logs.
    - Paths: all three M1 docs
    - Acceptance: Signed-off DoD checklist.
    - Risk: Proceeding to M2 with weak migration baseline.

### Critical path summary
Critical path is: **M1-01 → M1-02 → M1-03 → M1-04 → M1-05 → M1-06 + M1-07 → M1-08 → M1-11 → M1-15**.

---

## D) Acceptance Criteria / Definition of Done for M1

M1 is done only if all conditions are met:

1. **Migration history exists and is consistent**
   - `backend/alembic/versions/` contains initial baseline revision.
   - `alembic history` and `alembic current` produce expected single-lineage results.

2. **Clean bootstrap is reproducible**
   - New developer can run documented commands (docker or local), apply migrations, and start API successfully.
   - No manual SQL required for baseline setup.

3. **Existing DB onboarding path is validated**
   - Procedure for snapshot/legacy DB is documented and tested (`stamp baseline`, then `upgrade head`, or equivalent documented safe path).
   - Procedure explicitly includes pre-checks and mismatch handling.

4. **Developer workflow is documented and testable**
   - Commands exist for: create migration, review migration, apply migration, rollback last migration.
   - Team checklist states when to use autogenerate and mandatory manual review.

5. **Safety controls are defined for pilot**
   - Backup-before-migrate is mandatory.
   - Rollback/restore runbook exists with clear decision thresholds.

6. **Scope boundaries are preserved**
   - No migration changes to controller SQLite journal in M1.
   - No destructive schema operations included in baseline milestone.

---

## Smoke Test Plan (for M1 verification)

### Scenario 1 — Clean DB bootstrap
1. Start fresh Postgres (empty volume).
2. Run `alembic upgrade head`.
3. Start backend API.
4. Verify API starts and core endpoints respond.

Expected:
- Schema exists after migration.
- Backend starts without schema errors.

### Scenario 2 — Existing DB snapshot onboarding
1. Restore representative pre-M1 snapshot.
2. Run schema parity check against baseline assumptions.
3. If parity confirmed: `alembic stamp <baseline_rev>`.
4. Run `alembic upgrade head`.
5. Smoke API read/write path.

Expected:
- No data loss.
- Migration state is registered and future upgrades work.

### Scenario 3 — Developer workflow drill
1. Create test additive migration (non-destructive).
2. Apply upgrade.
3. Roll back one revision.
4. Re-apply upgrade.

Expected:
- Workflow commands are reliable and documented.
- Team can repeat without ad-hoc fixes.

---

## E) Safety / Rollback Plan

### Pre-deploy safety gates (pilot)
- Mandatory DB backup before any migration run.
- Migration dry-run in staging/snapshot environment first.
- Deployment window with operator on standby.

### If baseline migration breaks pilot environment
1. **Stop write traffic** (pause admin operations that mutate DB).
2. **Capture failure artifacts** (migration logs, current revision, DB error).
3. **Attempt controlled rollback** only if migration is rollback-safe and tested.
4. If rollback is uncertain, **restore from pre-migration backup**.
5. Re-open system on restored DB and log incident with root cause.
6. Patch migration script/process in staging before next attempt.

### Roll-forward preference
- Prefer roll-forward fixes when data integrity is preserved.
- Use restore path when integrity is uncertain or service must recover quickly.

---

## Implementation Options

## Option A — Minimal baseline (fastest, safest for demo/pilot) **[Recommended]**
- Commit initial Alembic baseline revision.
- Document clean bootstrap + stamp-based existing DB onboarding.
- Keep changes limited to migration discipline docs and minimal migration scripts.
- Delay broader refactors (e.g., full startup lifecycle hardening) to post-M1 unless required for immediate safety.

Pros:
- Lowest disruption risk.
- Fastest readiness for pilot and investor demo continuity.
- Aligns with M1 intent in pipeline doc.

Cons:
- Some technical debt remains (e.g., temporary coexistence concerns around `create_all` until follow-up closure).

## Option B — Fuller baseline (more disciplined, slightly slower)
- Everything in Option A, plus:
  - Immediate migration-only startup enforcement (remove/disable `create_all` now).
  - CI migration job and stricter PR gates in same milestone.
  - Stronger environment unification for Alembic/backend URL handling.

Pros:
- Better long-term discipline immediately.
- Lower drift risk after completion.

Cons:
- Higher short-term change surface and regression risk before pilot.
- More coordination/time needed.

### Recommendation
Choose **Option A** for current pilot/investor phase: establish the migration baseline quickly and safely, then schedule Option B hardening immediately after M1 sign-off (or as M1.5) to avoid destabilizing demo-critical flow.
