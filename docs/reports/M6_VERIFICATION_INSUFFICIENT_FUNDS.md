# M6 Verification Report: Insufficient Funds Clamp

Date: 2026-02-28
Branch: `m6/insufficient-funds-clamp`

## Scope

- hard deny on `authorize-pour` when balance cannot cover `min_start_ml`
- backend-provided `max_volume_ml` clamp respected by controller
- terminal sync outcomes for stale/missing authorize paths
- lock and `processing_sync` cleanup in terminal paths
- runtime configurability of `min_start_ml` via `system_states`

## Branch state

- `git status --short --branch` -> clean working tree before final verification
- `git rev-list --left-right --count origin/master...HEAD` -> `0 7`
- Result: hotfix branch does not lag behind `origin/master`; rebase was not required

## Executed commands

### Docker / Postgres

Note: `docker compose exec` requires a running `beer_backend_api` container, so the API container was started before the `exec` step.

```powershell
docker compose down -v
docker compose up -d postgres
docker compose up -d beer_backend_api
docker compose exec -T beer_backend_api alembic upgrade head
docker compose exec -T beer_backend_api alembic heads
docker compose exec -T beer_backend_api pip install -r requirements-test.txt
```

Result:
- `docker compose down -v` completed, PostgreSQL volume removed
- `alembic upgrade head` applied cleanly from `0001_m1_baseline` through `0012_m6_rejected_sync`
- `alembic heads` returned a single head: `0012_m6_rejected_sync (head)`

Migration log fragment:

```text
INFO  [alembic.runtime.migration] Running upgrade 0010_m5_db_time_source -> 0011_m6_insufficient_funds_clamp, M6 insufficient funds clamp defaults
INFO  [alembic.runtime.migration] Running upgrade 0011_m6_insufficient_funds_clamp -> 0012_m6_rejected_sync, M6 rejected pour terminal state
```

### Pytests (Postgres)

Executed command:

```powershell
docker compose exec -T -e TEST_USE_POSTGRES=1 -e TEST_DATABASE_URL=postgresql://beer_user:beer_password@postgres:5432/beer_tap_db_test beer_backend_api python -m pytest tests/test_m6_insufficient_funds_clamp.py tests/test_m3_tap_lock.py tests/test_m4_offline_sync_reconcile.py tests/test_m5_shift_operational_mode.py tests/test_m6_lost_cards.py -q
```

Result:
- `32 passed in 21.43s`

Covered files:
- `tests/test_m6_insufficient_funds_clamp.py`
- `tests/test_m3_tap_lock.py`
- `tests/test_m4_offline_sync_reconcile.py`
- `tests/test_m5_shift_operational_mode.py`
- `tests/test_m6_lost_cards.py`

Pytest output fragment:

```text
................................                                         [100%]
32 passed in 21.43s
```

### Encoding guard

Executed command:

```powershell
python scripts/encoding_guard.py --all
```

Result:

```text
[encoding_guard] Scanning 236 file(s).
[encoding_guard] OK: no UTF-8/mojibake/bidi-control issues found.
```

## Runtime business parameter: `min_start_ml`

Current implementation already reads `min_start_ml` from `system_states`; code change is not required to raise it from `20` to `50`.

Verified by regression test:
- `test_authorize_uses_runtime_min_start_ml_from_system_states`

Operational update example for raising the threshold to `50` ml:

```sql
INSERT INTO system_states (key, value)
VALUES ('min_start_ml', '50')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

Expected effect:
- authorize deny threshold becomes the cost of `50` ml instead of `20` ml
- `detail.context.min_start_ml` and `required_cents` reflect the new runtime value
- no code redeploy is required

## Verify on hardware

Target duration: `10-15` minutes.

1. Open shift, open visit, and bind the card.
2. Set guest balance below the cost of `min_start_ml`.
3. Present the card.
Expected:
- authorize is denied
- valve does not open at all
- controller shows "Недостаточно средств"
- card must be removed before retry

4. Top up to slightly above the minimum threshold.
5. Present the card again.
Expected:
- authorize returns/uses `max_volume_ml`
- pouring starts
- controller closes the valve on the clamp
- sync updates the same pour to `sync_status=synced`

6. Trigger `sync without authorize`.
Expected:
- backend returns `audit_only`
- no new pour appears in `/api/pours`

7. Repeat a reject/audit path and then retry with a valid card.
Expected:
- no stuck `card already in use`
- no stuck `processing_sync`

## Minimal hardware evidence to capture

- Fragment 1: controller/operator log showing deny on insufficient funds with no valve open
- Fragment 2: admin/app or API view showing synced pour after clamp stop, or `audit_only` result for sync-without-authorize

## SQL spot checks

```sql
SELECT key, value
FROM system_states
WHERE key IN ('min_start_ml', 'safety_ml', 'allowed_overdraft_cents');

SELECT sync_status, short_id, volume_ml, authorized_at, synced_at
FROM pours
ORDER BY created_at DESC
LIMIT 10;

SELECT action, target_id, details, timestamp
FROM audit_logs
WHERE action IN (
    'insufficient_funds_blocked',
    'audit_missing_pending',
    'sync_rejected_insufficient_funds',
    'sync_rejected_insufficient_keg_volume'
)
ORDER BY timestamp DESC
LIMIT 10;
```
