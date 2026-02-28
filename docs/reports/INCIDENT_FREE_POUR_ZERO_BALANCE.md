# INCIDENT: Free Pour With Zero Balance

Date: 2026-02-28

Investigation baseline:
- `origin/master` HEAD: `b2a37ae999979c1d9419d0a8779f95872dec779c`
- Alembic head/current during reproduction: `0010_m5_db_time_source`
- Incident branch: `incident/free-pour-zero-balance`

Artifacts:
- `docs/reports/artifacts/incident_free_pour/00_infra_before_fix.log`
- `docs/reports/artifacts/incident_free_pour/01_api_repro_before_fix.log`
- `docs/reports/artifacts/incident_free_pour/backend_logs_before_fix.txt`
- `docs/reports/artifacts/incident_free_pour/02_api_repro_after_fix.log`
- `docs/reports/artifacts/incident_free_pour/backend_logs_after_fix.txt`

## Summary

Critical safety bug confirmed on `origin/master`.

On current backend/controller code:
- controller asks backend `POST /api/visits/authorize-pour`
- backend returned `200 allowed=true` even when guest balance was `0.00`
- controller therefore had valid ALLOW and opened valve
- later `POST /api/sync/pours` returned `status="rejected"` / `outcome="rejected_insufficient_funds"`
- no money was charged, no transaction was created, and backend did not create an audit event for the rejection

That is enough to produce a real free pour.

Additional defect found:
- if sync arrives with visit lock present but backend `pending_sync` row missing, backend could return `accepted` with `outcome="synced_without_pending"` and silently create a synced pour
- this violates the operational invariant that backend must never accept controller sync as confirmed when authorize/pending state is missing

## Impact

- Free product can be dispensed to a guest with zero or near-zero balance.
- Financial accounting is bypassed for that pour.
- Original `master` left visit/tap stuck in `pending_sync` / `processing_sync` after rejected sync, creating an operational deadlock.
- Rejected sync on insufficient funds had no dedicated audit trail, so incident analysis was harder than necessary.

## Reproduction

### Docker reproduction on `origin/master`

1. `docker compose down -v`
2. `docker compose up -d postgres`
3. `docker compose run --rm beer_backend_api alembic upgrade head`
4. `docker compose up -d beer_backend_api`
5. Create:
   - open shift
   - guest with balance `0.00`
   - card bound to guest
   - active visit
   - beverage + keg + tap
6. Mimic controller:
   - `POST /api/visits/authorize-pour` with `X-Internal-Token`
   - `POST /api/sync/pours` with controller payload

Observed before fix:
- `authorize-pour` returned `200` with `allowed=true`
- `sync/pours` returned `200` with:
  - `status="rejected"`
  - `outcome="rejected_insufficient_funds"`
- DB state after sync:
  - `guests.balance` unchanged at `0.00`
  - `transactions` unchanged
  - `pours` contained only the zero-volume `pending_sync` row created at authorize
  - `visits.active_tap_id` remained locked
  - no dedicated audit row for insufficient funds rejection

Concrete runtime evidence:
- request `incident-free-pour-auth-94306` in `backend_logs_before_fix.txt`
- request `incident-free-pour-sync-94306` in `backend_logs_before_fix.txt`

### Hardware notes

Current repo controller does not ignore backend deny.

`rpi-controller/flow_manager.py` opens valve only when `sync_manager.authorize_pour()` returns `allowed=true`.

Therefore, in this repo, valve opening at zero balance comes from backend incorrectly authorizing the pour, not from controller bypassing deny.

## Root Cause Analysis

### Why valve opened at zero balance

Root cause:
- `backend/crud/visit_crud.py::authorize_pour_lock()` had no balance gate at all.

Actual behavior on `master`:
- lost-card check existed
- active visit check existed
- tap lock was set
- `pending_sync` row was created
- response returned `allowed=true`

There was no funds check before ALLOW.

Conclusion:
- backend was the direct source of incorrect operational permission
- controller behavior was consistent with current contract: it received ALLOW and opened valve

### Why pour was not financially processed after sync

`backend/crud/pour_crud.py::process_pour()` performed the money check only on sync:
- calculates `amount_to_charge`
- if `guest.balance < amount_to_charge`, returns:
  - `status="rejected"`
  - `outcome="rejected_insufficient_funds"`

Effects on `master`:
- no debit
- no volume decrement
- no transaction
- no synced pour row
- no dedicated audit trail for this rejection

This created the "free pour already happened, backend rejects later" failure mode.

### Why backend state became inconsistent

Because authorize had already created `pending_sync` and locked the visit:
- `visits.active_tap_id` stayed set
- tap stayed `processing_sync`
- zero-volume placeholder `pending_sync` row remained unresolved

So the incident was not only free-pour accounting loss, but also left recovery work for operators.

### Additional RCA: missing-pending sync acceptance

Separate but related defect:
- if visit lock existed but `pending_sync` row was missing, `process_pour()` could still return `accepted` with `outcome="synced_without_pending"`

This violated the stated invariant:
- backend must not silently accept a pour when authorize/pending state is absent
- anomaly must be explicit and audited

This path was not needed for the zero-balance exploit itself, but it was a real contract hole and was fixed in the same hotfix.

### Note about live observation "`/api/pours` was empty"

Local reproduction on `origin/master` did not fully match that detail.

What was observed locally:
- `/api/pours` showed the zero-volume `pending_sync` placeholder created during authorize

Inference:
- either the live system was on a different build/path than current `master`
- or the operator/UI observation referred to "no completed synced pours", not literally no rows in `pours`

This discrepancy does not change the confirmed primary RCA:
- backend incorrectly granted ALLOW at authorize time with zero balance

## Fix Description

### A. Authorize hard-denies insufficient funds

Changed:
- `backend/crud/visit_crud.py`
- `backend/api/visits.py`

Behavior now:
- backend computes minimum possible charge for the selected tap (`sell_price_per_liter / 1000`)
- if guest balance is below that amount:
  - return `403`
  - `detail.reason = "insufficient_funds"`
  - `detail.message = "Insufficient funds: top up guest balance before pouring."`
  - do not set `active_tap_id`
  - do not set `lock_set_at`
  - do not create `pending_sync`
  - write audit event `insufficient_funds_denied`

### B. Controller does not open valve on insufficient funds

Changed:
- `rpi-controller/flow_manager.py`

Behavior now:
- controller already required backend ALLOW before opening valve
- hotfix adds explicit `insufficient_funds` handling:
  - logs operator-facing Russian warning
  - enters `CARD_MUST_BE_REMOVED`
  - valve stays closed

### C. Sync without valid pending authorize is explicit and audited

Changed:
- `backend/crud/pour_crud.py`

Behavior now:
- if visit lock exists but matching backend `pending_sync` row is missing:
  - return `status="audit_only"`
  - `outcome="audit_missing_pending"`
  - `reason="missing_pending_authorize"`
  - write audit event `sync_missing_pending`
  - do not create a pour row

Also added:
- audit event `sync_rejected_insufficient_funds` for sync-time insufficient-funds rejection path

This keeps M4 offline semantics intact:
- late sync after cleared lock still stays `audit_only`
- manual reconcile semantics are unchanged
- accepted sync still requires valid authorize/pending state

## Tests

Added:
- `backend/tests/test_incident_free_pour_zero_balance.py`
  - `test_authorize_denies_when_balance_zero`
  - `test_sync_without_authorize_returns_audit_only_not_accepted`
- `rpi-controller/test_flow_manager.py`
  - `test_controller_does_not_open_valve_on_insufficient_funds`

## How To Verify

### Operator/developer verification after deploy

1. Open shift and create a guest with zero balance.
2. Bind card, open visit, configure active tap with keg.
3. Call `POST /api/visits/authorize-pour` with controller token.
4. Expect `403` with `detail.reason="insufficient_funds"`.
5. Verify:
   - visit lock is still empty
   - no `pending_sync` pour exists for that visit
   - audit contains `insufficient_funds_denied`
6. Present the same card on controller:
   - valve must stay closed
   - controller must move to card-removal state

### Developer negative-path verification for missing pending

1. Prepare active visit with positive balance and active tap.
2. Simulate broken state where visit lock exists but `pending_sync` row is absent.
3. Send `POST /api/sync/pours`.
4. Expect:
   - HTTP `200`
   - `status="audit_only"`
   - `outcome="audit_missing_pending"`
   - no created pour row
   - audit event `sync_missing_pending`

## Regression Risks

- Authorize deny now uses minimum possible charge (`price_per_ml`), so extremely small positive balances below 1 ml price are also denied. This is intentional and consistent with "no pour without ability to pay at least the smallest charge unit".
- Legacy stuck visits created before this hotfix can still exist and require operator recovery.
- Live-system observation "`/api/pours` empty" was not reproduced on current `master`; if that exact symptom is still seen after deploy, it likely points to a separate UI/build drift and should be investigated independently.
