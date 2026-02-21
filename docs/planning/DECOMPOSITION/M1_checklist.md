# M1 Migration Baseline — Execution Checklist

## Phase 0 — Scope and Decisions
- [ ] Confirm M1 scope = backend PostgreSQL migration discipline only.
- [ ] Confirm controller SQLite migration is out-of-scope for M1.
- [ ] Confirm M1 decisions:
  - [ ] Remove/disable `Base.metadata.create_all()` in M1.
  - [ ] Alembic is single schema writer from M1 onward.
  - [ ] Downgrade drill is minimal (one-time on latest/simple revision).

## Phase 1 — Baseline Preparation
- [ ] Verify schema touchpoints:
  - `backend/models.py`
  - `backend/main.py`
  - `backend/alembic/*`
- [ ] Confirm env contract for app and migrations (`DATABASE_URL`, `POSTGRES_*`).
- [ ] Document migration policy (additive-first, no destructive ops in M1).

## Phase 2 — Baseline Migration
- [ ] Create initial Alembic baseline revision.
- [ ] Manually review generated DDL for safety.
- [ ] Commit baseline migration files.

## Phase 3 — Runtime Cutover to Alembic-Only
- [ ] Remove/disable startup `create_all` usage in `backend/main.py`.
- [ ] Validate that schema creation is not performed by app startup.
- [ ] Ensure documented startup sequence requires migrations first.

## Phase 4 — Smoke Validation

### Clean bootstrap
- [ ] Recreate empty Postgres.
- [ ] Run `alembic upgrade head`.
- [ ] Start backend API.
- [ ] Verify health endpoint and basic API access.

### Existing DB onboarding
- [ ] Restore representative existing DB snapshot.
- [ ] Perform schema parity check with baseline.
- [ ] Run `alembic stamp <baseline_rev>` only if parity matches.
- [ ] Run `alembic upgrade head`.
- [ ] Verify data intact + basic read/write flow.

### Minimal downgrade capability check
- [ ] Execute one-step downgrade on simple/latest revision.
- [ ] Re-upgrade to head.
- [ ] Record result as capability proof (no expanded downgrade runbook required in M1).

## Phase 5 — Team Guardrails
- [ ] Document dev command workflow (revision/create, upgrade, history/current).
- [ ] Add migration PR review checklist (additive, defaults/nullability, data safety).
- [ ] Freeze direct manual DDL outside migration scripts (except emergency recovery).

## Phase 6 — Pilot Safety Readiness
- [ ] Document backup-before-migration requirement.
- [ ] Document lightweight recovery decision path (downgrade-if-applicable else restore backup).
- [ ] Assign migration author/reviewer/operator ownership.
- [ ] Collect sign-off evidence for DoD.

---

## Critical Path Checklist
- [ ] Baseline created.
- [ ] `create_all` removed/disabled.
- [ ] Clean bootstrap via Alembic validated.
- [ ] Existing DB onboarding validated.
- [ ] One-time minimal downgrade check validated.
- [ ] DoD signed off.

---

## M1 Definition of Done (Gate)
- [ ] Baseline migration history is committed and consistent.
- [ ] `Base.metadata.create_all()` is removed/disabled from runtime path.
- [ ] Alembic is documented and operational as the single schema writer.
- [ ] New developer can bootstrap clean DB and start project from documented steps.
- [ ] Existing DB onboarding path is validated (or equivalently tested and documented).
- [ ] One minimal downgrade capability check is recorded.
- [ ] Backup/recovery notes are documented for pilot execution.
