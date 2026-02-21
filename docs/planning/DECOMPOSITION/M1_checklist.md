# M1 Migration Baseline — Execution Checklist

## Phase 0 — Scope Lock
- [ ] Confirm M1 scope = backend PostgreSQL migration discipline only.
- [ ] Confirm out-of-scope for M1 = controller SQLite journal migration.
- [ ] Confirm no destructive schema work in M1.

## Phase 1 — Baseline Preparation
- [ ] Verify current schema owners:
  - `backend/models.py` (ORM schema)
  - `backend/main.py` (`create_all` currently active)
  - `backend/alembic/*` (migration tooling)
- [ ] Confirm env contracts used by app and migrations:
  - App: `DATABASE_URL`
  - Alembic: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_DB` (current `env.py` behavior)
- [ ] Decide M1 policy for `create_all` coexistence vs migration-only startup endpoint.

## Phase 2 — Baseline Revision
- [ ] Create initial Alembic baseline revision representing current backend schema.
- [ ] Ensure baseline revision has clear message/tag (`m1_baseline` style).
- [ ] Review generated DDL manually for unsafe/destructive operations.
- [ ] Commit migration revision(s) and any required Alembic config adjustments.

## Phase 3 — Smoke Validation

### Clean bootstrap (empty DB)
- [ ] Recreate clean Postgres volume/container.
- [ ] Run migration apply to head.
- [ ] Start backend API.
- [ ] Verify core API health endpoint responds.

### Existing DB snapshot onboarding
- [ ] Restore representative existing DB snapshot.
- [ ] Validate schema parity against expected baseline.
- [ ] Run baseline registration (`stamp`) if schema already matches.
- [ ] Run migration apply to head.
- [ ] Validate data presence and basic API reads.

### Developer workflow drill
- [ ] Create a sample additive migration (test-only workflow exercise).
- [ ] Apply upgrade.
- [ ] Downgrade one step.
- [ ] Upgrade again.
- [ ] Confirm no manual DB repair needed.

## Phase 4 — Team Workflow and Guardrails
- [ ] Document migration command cookbook:
  - create revision
  - upgrade head
  - current/history
  - downgrade -1
- [ ] Document PR review checklist for migration scripts:
  - additive-first policy
  - nullable/default strategy for new columns
  - rollback path and data safety
- [ ] Explicitly prohibit direct schema edits outside migration scripts (except emergency runbook path).

## Phase 5 — Pilot Safety Readiness
- [ ] Document backup-before-migration runbook.
- [ ] Document rollback/restore decision tree.
- [ ] Define migration execution window and operator ownership for pilot.
- [ ] Capture final evidence artifacts (logs/screenshots/command outputs).

---

## Critical Path Checklist
- [ ] Scope lock approved.
- [ ] Baseline revision created and reviewed.
- [ ] Clean bootstrap validated.
- [ ] Existing DB onboarding validated.
- [ ] Rollback/restore runbook validated.
- [ ] M1 DoD formally signed off.

---

## M1 Definition of Done (Gate)
- [ ] A committed migration history exists from baseline to head.
- [ ] New developer can bootstrap DB from empty state and start project using documented commands.
- [ ] Existing DB upgrade path is validated OR a precise, tested onboarding/stamp procedure is documented.
- [ ] Team workflow for creating/applying/rolling back migrations is documented and repeatable.
- [ ] Pilot rollback safety plan is documented and accepted by owners.
