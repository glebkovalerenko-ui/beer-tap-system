# PRE-M7 Closing Audit

Date: 2026-03-01

## Current master revision + alembic head

- Current `master` / `origin/master`: `7630de9622e3a8988c7ede574010be34859a0a65`
- Current Alembic head on `master`: `0012_m6_rejected_sync`
- Clean boot verification:
  - `docker compose down -v`
  - `docker compose up -d postgres`
  - `docker compose run --rm beer_backend_api alembic upgrade head`
  - `docker compose up -d beer_backend_api`
  - `curl.exe http://localhost:8000/`
  - `docker compose exec -T beer_backend_api alembic current`
  - `docker compose exec -T beer_backend_api alembic heads`
- Clean boot result:
  - upgrade path succeeded from `0001_m1_baseline` through `0012_m6_rejected_sync`
  - `alembic current` = `0012_m6_rejected_sync (head)`
  - `alembic heads` = `0012_m6_rejected_sync (head)`
  - root healthcheck returned `{"Status":"Beer Tap System Backend is running!"}`

## Inventory snapshot

### Initial repo / PR state

- `git fetch origin`: executed before housekeeping
- `origin/master` HEAD at start of audit: `b2a37ae999979c1d9419d0a8779f95872dec779c`
- `gh pr list --state open` at start:

| PR | Title | Base | Head | Status checks |
| --- | --- | --- | --- | --- |
| #38 | M6: narrow controller terminal UX changes | `master` | `m6/controller-terminal-ux-clean` | `encoding-guard`, `backend-smoke`, `frontend-build` = SUCCESS |
| #36 | M6 hotfix: prevent pours with insufficient funds (authorize clamp + terminal sync outcomes) | `master` | `m6/insufficient-funds-clamp` | `encoding-guard`, `backend-smoke`, `frontend-build` = SUCCESS |

- Superseded PR check:
  - PR #37 was already `CLOSED`

### Housekeeping outcome

- `gh pr list --state open` after completion: empty
- Maximum open PRs after completion: `0`

## List of PR merged/closed

- Merged: [#38 M6: narrow controller terminal UX changes](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/38)
- Merged: [#36 M6 hotfix: prevent pours with insufficient funds (authorize clamp + terminal sync outcomes)](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/36)
- Confirmed closed superseded PR: [#37 M6: improve controller terminal UX](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/37)
- Additional minimal fix on `master` after full smoke:
  - `7630de9` `HOTFIX: align controller sync BDD with missing pending authorize outcome`
  - Scope: update stale BDD expectation to current `sync/pours` contract after clamp hotfix

## PR housekeeping notes

- After merging `#38`, post-merge smoke on an existing stateful Postgres volume exposed a revision gap:
  - DB already held `0012_m6_rejected_sync`
  - `master` only knew up to `0010_m5_db_time_source`
  - Result: `alembic upgrade head/current` failed on the existing DB
- Resolution:
  - rebased `#36` locally on top of updated `master`
  - resolved conflicts in `rpi-controller/flow_manager.py` and `rpi-controller/sync_manager.py`
  - preserved `#38` terminal UX changes and `#36` clamp / terminal outcome logic
  - re-ran controller smoke and Postgres targeted regressions
  - pushed rebased branch and merged `#36`
- Post-merge `master` smoke after `#36`:
  - `git pull origin master` = OK
  - `docker compose exec -T beer_backend_api alembic upgrade head` = OK
  - `docker compose exec -T beer_backend_api alembic current` = `0012_m6_rejected_sync (head)`
  - `curl.exe http://localhost:8000/` = OK

## E2E scenario

Environment:

- Scenario executed once on clean `master` after `docker compose down -v`
- Backend target: local compose PostgreSQL + FastAPI
- Admin-app integration was checked through:
  - successful `npm --prefix admin-app run build`
  - runtime contracts used by `admin-app/src/stores/visitStore.js` (`GET /api/visits/active`)
  - runtime contracts used by `admin-app/src/stores/pourStore.js` (`GET /api/pours/?limit=20`)
- Controller integration was checked through:
  - real `sync/pours` / authorize flow in E2E run
  - local controller smoke tests for merged conflict surface

### 1. Shift

Commands:

- `POST /api/visits/open` with `guest_id` while shift closed
- `POST /api/visits/authorize-pour` while shift closed
- `POST /api/shifts/open`

Expected:

- visit open denied with `403` / `Shift is closed`
- authorize denied with `403` / `detail.reason=shift_closed`
- shift opens with `200` / `status=open`

Actual:

- `403` `Shift is closed`
- `403` `{"reason":"shift_closed","message":"Shift is closed"}`
- `200` `{"status":"open","id":"2cd51431-cfb8-4e6f-91ef-07778520998d"}`

Result: `PASS`

### 2. Guest + Visit + Card

Commands:

- `POST /api/guests/`
- `POST /api/visits/open` without `card_uid`
- `POST /api/visits/{visit_id}/assign-card`
- `GET /api/visits/active`

Expected:

- guest created
- active visit opens without card
- card can be attached to active visit via API NFC-equivalent flow
- active visit is visible in admin-app source with `active_tap_id=null` and `lock_set_at=null`

Actual:

- guest created `201`
- visit opened `200` with `card_uid=null`
- card assigned `200` with `card_uid="CARD-PREM7-98001"`
- `GET /api/visits/active` returned the visit with:
  - `active_tap_id=null`
  - `lock_set_at=null`

Result: `PASS`

### 3. Top-up + authorize clamp

Commands:

- `POST /api/guests/{guest_id}/topup` amount `9.0`
- `POST /api/visits/authorize-pour`
- `POST /api/guests/{guest_id}/topup` amount `11.0`
- `POST /api/visits/authorize-pour`

Expected:

- low balance case denied with `403` / `reason=insufficient_funds`
- no valve-open path is created on deny
- sufficient balance case returns `200` with `max_volume_ml`

Actual:

- deny response:
  - `403`
  - `reason=insufficient_funds`
  - context included `min_start_ml=20`, `max_volume_ml=16`, `price_per_ml_cents=50`, `balance_cents=900`
- allow response:
  - `200`
  - `allowed=true`
  - `max_volume_ml=38`

Result: `PASS`

### 4. Pour lifecycle

Commands:

- `GET /api/visits/active`
- `GET /api/pours/?limit=20`
- `POST /api/sync/pours`
- `GET /api/pours/?limit=20`
- `GET /api/visits/active/by-card/{card_uid}`

Expected:

- authorize creates `pending_sync`
- admin-app active visit source shows `active_tap_id` and `lock_set_at`
- sync converts `pending_sync -> synced`
- pour appears in `/api/pours`
- lock clears after sync

Actual:

- `GET /api/visits/active` showed:
  - `active_tap_id=1`
  - non-null `lock_set_at`
- `GET /api/pours/?limit=20` showed pending placeholder:
  - `sync_status=pending_sync`
  - `volume_ml=0`
- `POST /api/sync/pours` returned:
  - `status=accepted`
  - `outcome=pending_updated_to_synced`
- `GET /api/pours/?limit=20` then showed:
  - `short_id=PM7001`
  - `sync_status=synced`
  - `amount_charged=15.00`
- `GET /api/visits/active/by-card/...` showed `active_tap_id=null`

Result: `PASS`

### 5. Offline / reconcile

Commands:

- `POST /api/sync/pours` without prior authorize on another active visit
- `GET /api/pours/?limit=20`
- `GET /api/audit/`
- `POST /api/visits/{visit_id}/reconcile-pour`
- repeat same `POST /api/visits/{visit_id}/reconcile-pour`
- `POST /api/sync/pours` late-match
- `POST /api/sync/pours` late-mismatch
- `GET /api/guests/{guest_id}`

Expected:

- sync without authorize returns `audit_only`
- no pour row created for that late sync
- audit row written
- manual reconcile clears lock
- reconcile is idempotent
- late match/mismatch do not double-charge

Actual:

- sync without authorize returned:
  - `200`
  - `status=audit_only`
  - `outcome=audit_late_recorded`
  - `reason=late_sync_mismatch_recorded`
- `GET /api/pours/?limit=20` confirmed no `short_id=PM7LATE1`
- `GET /api/audit/` contained `late_sync_mismatch`
- first reconcile:
  - `200`
  - `active_tap_id=null`
- second reconcile:
  - `200`
  - still `active_tap_id=null`
- late match returned `audit_only / audit_late_matched`
- late mismatch returned `audit_only / audit_late_recorded`
- guest balance stayed `50.00` before and after late syncs

Result: `PASS`

### 6. Lost card

Commands:

- `POST /api/visits/{visit_id}/report-lost-card`
- `POST /api/visits/authorize-pour`
- `POST /api/lost-cards/{card_uid}/restore`
- `POST /api/visits/authorize-pour`
- `POST /api/sync/pours`

Expected:

- lost-card mark is created
- authorize denied with `reason=lost_card`
- restore re-enables authorize
- successful sync after restore clears pending path

Actual:

- report lost card:
  - `200`
  - `lost=true`
- authorize while lost:
  - `403`
  - `reason=lost_card`
- restore:
  - `200`
  - `restored=true`
- authorize after restore:
  - `200`
  - `allowed=true`
  - `max_volume_ml=198`
- sync after restore:
  - `200`
  - `status=accepted`

Result: `PASS`

### 7. Shift close + X/Z reports

Commands:

- `POST /api/visits/{visit_id}/close` while pending sync exists
- `GET /api/shifts/{shift_id}/reports/x`
- `POST /api/shifts/close` while active visits still exist
- `POST /api/visits/{visit_id}/close` for all active visits
- `POST /api/shifts/close`
- `POST /api/shifts/{shift_id}/reports/z`
- `GET /api/shifts/{shift_id}/reports/z`
- `GET /api/shifts/reports/z?from=2026-03-01&to=2026-03-01`

Expected:

- visit close blocked by `pending_sync_exists_for_visit`
- X report available during open shift
- shift close blocked while active visits exist
- shift closes after visits are closed
- Z report is created, idempotently fetchable, and listed by date

Actual:

- close active visit with pending sync:
  - `409`
  - `detail=pending_sync_exists_for_visit`
- X report:
  - `200`
  - `report_type=X`
  - `pours_count=3`
  - `pending_sync_count=0`
- shift close while active visits exist:
  - `409`
  - `detail=active_visits_exist`
- all active visits closed successfully
- shift closed:
  - `200`
  - `status=closed`
- Z report created:
  - `200`
  - `report_type=Z`
  - `report_id=9db73384-ee6a-4792-abad-706bb9bd6784`
- Z report fetch returned same `report_id`
- date listing included the closed shift

Result: `PASS`

## Regression tests

Postgres targeted suite:

- `docker compose exec -T -e TEST_USE_POSTGRES=1 -e TEST_DATABASE_URL=postgresql://beer_user:beer_password@postgres:5432/beer_tap_db_test beer_backend_api python -m pytest tests/test_m3_tap_lock.py tests/test_m4_offline_sync_reconcile.py tests/test_m5_shift_operational_mode.py tests/test_m5_shift_reports_v1.py tests/test_m6_lost_cards.py tests/test_m6_insufficient_funds_clamp.py -q`
- Result: `37 passed in 26.43s`

Backend smoke on Postgres:

- `docker compose exec -T -e TEST_USE_POSTGRES=1 -e TEST_DATABASE_URL=postgresql://beer_user:beer_password@postgres:5432/beer_tap_db_test beer_backend_api python -m pytest -q`
- First parallel attempt was invalid due test DB creation race in `conftest.py` when two suites tried to create `beer_tap_db_test` simultaneously
- Sequential rerun result: `95 passed, 5 skipped, 1 warning in 51.37s`

Controller smoke:

- `python -m pytest -q rpi-controller/test_flow_manager.py rpi-controller/test_terminal_progress.py rpi-controller/test_pour_session.py rpi-controller/test_log_throttle.py`
- Result: `8 passed in 0.24s`

Admin-app:

- `npm --prefix admin-app run build` -> PASS
- `npm --prefix admin-app run check` -> FAIL
  - current result: `378 errors in 46 files`
  - classification: pre-existing static typing debt, not a runtime regression introduced by this closing pass

## Known limitations

- Денежные единицы / отображение рублей и копеек intentionally not changed; this remains deferred to POS UI, as requested.
- `admin-app` production build succeeds, but `npm run check` still fails on pre-existing JS/Svelte typing debt.
- Full backend suite should be run sequentially against a shared Postgres test DB; parallel runs can race on `CREATE DATABASE beer_tap_db_test`.
- One warning remains in backend smoke:
  - `controller_crud.py` still uses deprecated Pydantic `.dict()` instead of `model_dump()`
  - this did not break tests and was not touched in this pass because it is outside the integration-closing scope

## Blockers

- None for M7 integration start.

## Minimal fix plan for non-blocking leftovers

- `admin-app` typecheck debt:
  - separate cleanup pass for store typings / `never[]` inference / `import.meta.env` typing
- test DB race:
  - make `_ensure_postgres_database_exists()` idempotent under concurrent runners or isolate DB names per suite
- Pydantic deprecation warning:
  - swap `controller.dict()` to `controller.model_dump()` in a dedicated maintenance commit

## Verdict

`READY FOR M7 = YES`
