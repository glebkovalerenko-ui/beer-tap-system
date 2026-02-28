# M6 Incident Report: Zero / Near-Zero Balance Pour

Date: 2026-02-28

## Reproduction

Environment:
- `docker compose up -d postgres beer_backend_api`
- `docker compose exec -T beer_backend_api alembic upgrade head`

Live reproduction used a near-zero balance because the working tree already contained a partial 1 ml balance gate. Scenario:
1. Open shift.
2. Create guest, bind card, open visit.
3. Create beverage/keg/tap and assign keg to tap.
4. Top up guest to `0.10`.
5. Use beverage price `10.00` per liter so current authorize logic still allows start.
6. Call `POST /api/visits/authorize-pour`.
7. Call `POST /api/sync/pours` with `volume_ml=20`.

Observed live API results:
- `authorize-pour` returned `200 allowed=true`.
- `sync/pours` returned `status="rejected"`, `outcome="rejected_insufficient_funds"`.
- Backend kept visit lock and tap in `processing_sync`.
- A `pending_sync` pour row remained with `volume_ml=0`, no `synced_at`, and no balance debit.

## Expected behavior

- If balance cannot safely cover the minimum start volume, backend must deny authorize.
- Valve must not open on deny.
- If authorize succeeds, controller must receive a hard current-pour limit and enforce it locally.
- Normal sync must update the existing authorize-created pour row to `synced`.

## Actual behavior

- Controller really calls `POST /api/visits/authorize-pour` before valve open.
- Authorize check was missing on `origin/master`; the carried local hotfix only checked approximately 1 ml worth of funds.
- This allowed start with zero/near-zero balance relative to the business minimum.
- Later sync calculated the full actual charge and rejected it, so money was not debited and the operational pour was not completed in backend state.

## Root cause

Primary cause:
- backend authorize policy did not enforce a business minimum start threshold and did not return a backend-authored max volume clamp.

Secondary causes:
- controller opened valve after any successful authorize without a locally enforceable `max_volume_ml`;
- backend sync path could only decide after the fact whether the final amount fit the remaining balance;
- when sync was rejected, backend left the authorize-created row in `pending_sync`, so there was physical beer flow but no completed synced pour record.

## Fix plan implemented

1. Add DB-backed runtime settings in `system_states`:
   - `min_start_ml=20`
   - `safety_ml=2`
   - `allowed_overdraft_cents=0`
2. Extend authorize response with `min_start_ml`, `max_volume_ml`, `price_per_ml_cents`, `balance_cents`, `allowed_overdraft_cents`, `safety_ml`, `lock_set_at`.
3. Deny authorize with `403 detail.reason="insufficient_funds"` when `max_volume_ml < min_start_ml`.
4. Write audit event `insufficient_funds_blocked`.
5. Store authorize-time price on the pending row and require sync to update that same row.
6. Keep late sync without authorize as `audit_only`, but treat active-lock anomalies without `pending_sync` as terminal reject with audit and stale-lock cleanup.
7. If sync still fails after authorize (for example, insufficient funds edge or missing pending row), convert the authorize-created row to `sync_status="rejected"` or reject terminally with audit, instead of leaving `pending_sync`/`processing_sync` hanging.
8. Make controller refuse valve open without `allowed=true` and `max_volume_ml > 0`, and close valve at `poured_ml >= max_volume_ml`.

## Post-fix verification

1. Prepare visit with balance below `min_start_ml` cost.
2. Confirm `POST /api/visits/authorize-pour` returns `403 insufficient_funds`.
3. Confirm no `pending_sync` row is created and valve never opens.
4. Prepare visit with sufficient balance.
5. Confirm authorize returns `max_volume_ml`.
6. Confirm successful sync updates the existing `pending_sync` row to `synced` and clears the visit lock.
7. Simulate post-authorize balance loss or missing pending row.
8. Confirm sync returns terminal `rejected`, writes audit, and clears stale `active_tap_id` / `processing_sync`.
