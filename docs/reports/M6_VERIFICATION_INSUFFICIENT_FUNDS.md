# M6 Verification Runbook: Insufficient Funds Clamp

## Environment

```powershell
docker compose up -d postgres beer_backend_api
docker compose exec -T beer_backend_api alembic upgrade head
cd backend
$env:TEST_USE_POSTGRES='1'
$env:DATABASE_URL='postgresql://beer_user:beer_password@127.0.0.1:5432/beer_tap_db'
python -m pytest tests/test_m6_insufficient_funds_clamp.py tests/test_m3_tap_lock.py tests/test_m4_offline_sync_reconcile.py tests/test_m5_shift_operational_mode.py tests/test_m6_lost_cards.py -q
cd ..
python scripts/encoding_guard.py
```

## Manual API smoke

1. Open shift and prepare guest/card/visit/tap.
2. Set guest balance below the minimum start requirement.
3. Call `POST /api/visits/authorize-pour`.
Expected:
- HTTP `403`
- `detail.reason="insufficient_funds"`
- `detail.context` contains `min_start_ml`, `max_volume_ml`, `price_per_ml_cents`, `balance_cents`
- no valve open on controller
- no new `pending_sync` row

4. Top up guest above the threshold and call authorize again.
Expected:
- HTTP `200`
- `allowed=true`
- `max_volume_ml >= min_start_ml`
- tap lock is set
- one `pending_sync` row exists

5. Start pour on controller and keep card in place until measured volume reaches the returned `max_volume_ml`.
Expected:
- controller closes valve at the clamp
- local journal stores the pour for sync

6. Run sync.
Expected:
- backend returns `status="accepted"`
- same backend pour row transitions `pending_sync -> synced`
- visit lock clears
- tap leaves `processing_sync`

## Hardware operator scenario

1. Guest presents card with insufficient balance.
Expected:
- controller shows Russian message about insufficient funds
- valve does not click open even briefly
- screen enters card-removal state

2. Guest tops up and retries.
Expected:
- pour starts only after fresh authorize
- pour stops automatically at backend-provided limit

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
WHERE action IN ('insufficient_funds_blocked', 'audit_missing_pending')
ORDER BY timestamp DESC
LIMIT 10;
```
