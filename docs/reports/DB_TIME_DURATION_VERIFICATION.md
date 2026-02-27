# DB Time + Duration Contract Verification

Date: 2026-02-27
Branch: m6-lost-cards

## What changed

- Controller -> backend sync payload is duration-first (`duration_ms`) and keeps backward compatibility for legacy `start_ts`/`end_ts`.
- Backend stores official lifecycle timestamps only from Postgres DB time:
  - `authorized_at` on pending row creation in authorize flow.
  - `synced_at` on `pending_sync -> synced` transition.
  - `reconciled_at` on manual reconcile.
- `pours` schema extended with:
  - `duration_ms` (nullable)
  - `authorized_at`, `synced_at`, `reconciled_at` (nullable timestamptz)
- Pour feed/API now exposes DB-driven timing fields (`ended_at`, `started_at`) and duration.
- No business lifecycle timestamp in runtime CRUD uses `datetime.now()`; DB time (`func.now()` / `server_default`) is used.

## Why

- Removes trust in controller absolute clock for official event time.
- Makes audit/reconciliation deterministic and tamper-resistant.
- Preserves rollout safety: legacy controllers still accepted while migrating to duration-first contract.

## Manual verification (10 steps)

1. Start clean infra:
   - `docker compose down -v`
   - `docker compose up -d postgres`
2. Apply migrations:
   - `docker compose run --rm beer_backend_api alembic upgrade head`
3. Start backend:
   - `docker compose up -d beer_backend_api`
4. Health check:
   - `curl http://localhost:8000/`
   - Expected: `{"Status":"Beer Tap System Backend is running!"}`
5. Authorize pour (`POST /api/visits/authorize-pour`) for active visit.
   - Expected: visit lock set (`active_tap_id=tap_id`, `lock_set_at != null`).
   - DB expected: pending pour exists with `sync_status='pending_sync'`, `authorized_at != null`.
6. Sync with duration-first payload (`POST /api/sync/pours`, include `duration_ms`).
   - Expected response per row: `status=accepted`.
   - DB expected: same row moves to `sync_status='synced'`, `duration_ms` stored, `synced_at != null`, visit lock cleared.
7. Legacy compatibility sync (send `start_ts` + `end_ts`, no `duration_ms`).
   - Expected: accepted.
   - DB expected: `duration_ms` computed from delta; official timestamps still DB-generated (`synced_at` from DB now).
8. Manual reconcile (`POST /api/visits/{visit_id}/reconcile-pour`) with optional `duration_ms`.
   - Expected: lock cleared, row marked `sync_status='reconciled'`.
   - DB expected: `reconciled_at != null`, no duplicate row for same `(visit_id, short_id)`.
9. Late sync with same `short_id` after reconcile.
   - Expected: `audit_only` + `late_sync_matched`; no second debit.
10. Late sync with different `short_id` after reconcile.
   - Expected: `audit_only` + `late_sync_mismatch_recorded`; no second debit.

## Expected SQL spot-checks

- Pending with DB authorize time:
  - `select sync_status, authorized_at from pours where sync_status='pending_sync';`
- Synced with duration:
  - `select sync_status, duration_ms, synced_at from pours where sync_status='synced';`
- Reconciled path:
  - `select sync_status, duration_ms, reconciled_at from pours where sync_status='reconciled';`
- No duplicate reconcile charge by short_id:
  - `select visit_id, short_id, count(*) from pours where short_id is not null group by visit_id, short_id having count(*) > 1;`

## Automated verification performed

- Full backend pytest on Postgres (`TEST_USE_POSTGRES=1`) passed.
- Targeted suites passed:
  - `tests/test_m4_offline_sync_reconcile.py`
  - `tests/test_m5_shift_reports_v1.py`
  - `tests/test_m6_lost_cards.py`
