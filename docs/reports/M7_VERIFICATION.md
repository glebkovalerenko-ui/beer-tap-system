# M7 Verification

Date: 2026-03-04

## Scope

- FIFO keg suggestion endpoint
- Admin assignment-flow FIFO hint
- POSAdapter stub notifications for top-up, refund, and finalized pours

## Minimal data model decision

- No new keg timestamp column was added.
- FIFO uses existing `kegs.created_at`.
- Current codebase has no dedicated `beer_type_id`; M7 maps `beer_type_id` to existing `beverage_id`.
- Eligible FIFO warehouse stock is:
  - same `beverage_id`
  - `status = full`
  - `current_volume_ml > 0`
  - not assigned to any tap (`tap.keg_id IS NULL`)
- Deterministic ordering is:
  1. `created_at ASC`
  2. `keg_id ASC`

## Demo data to create

1. Create one beverage.
2. Create at least three full kegs for that beverage.
3. Assign the newest keg manually to prove the UI still allows override.
4. Leave at least one older keg in warehouse state to verify FIFO suggestion.
5. Create one guest, bind a card, open a visit, perform top-up, optional refund, and one finalized pour.

## How to verify FIFO in UI

1. Open `Taps / Kegs`.
2. Start keg assignment for any free tap.
3. Pick a keg type in the dropdown by selecting any available keg of that beverage.
4. Check the `Рекомендованный кег (FIFO)` block.
5. Confirm the suggested keg is the oldest eligible keg for that beverage.
6. Click `Выбрать этот кег` to copy the recommendation into the existing selector.
7. Finish assignment manually with `Назначить кегу`.

Important:
- Recommendation does not change backend state by itself.
- Only the existing assignment action mutates tap/keg state.

## How to verify FIFO by API

Request:

```http
GET /api/kegs/suggest?beer_type_id=<beverage_uuid>
Authorization: Bearer <token>
```

Expected response shape:

```json
{
  "recommended_keg": { "...": "..." },
  "candidates_count": 3,
  "reason": "oldest_available",
  "ordering_keys_used": ["created_at", "keg_id"]
}
```

## How to see POS stub events

Option 1: backend logs

- Search backend logs for `[POS_STUB]`

Option 2: audit trail

- Query `audit_logs` for:
  - `pos_stub_topup_notified`
  - `pos_stub_refund_notified`
  - `pos_stub_pour_notified`

## Expected POS stub behavior

- Top-up emits exactly one stub event per transaction.
- Refund emits exactly one stub event per transaction.
- Finalized pour emits exactly one stub event per logical pour.
- Duplicate sync and late sync after manual reconcile must not create a second pour stub event.

## Verification commands

Backend / Postgres:

```powershell
docker compose down -v
docker compose up -d postgres
docker compose up -d beer_backend_api
docker compose exec -T beer_backend_api alembic upgrade head
docker compose exec -T -e TEST_USE_POSTGRES=1 -e TEST_DATABASE_URL=postgresql://beer_user:beer_password@postgres:5432/beer_tap_db_test beer_backend_api python -m pytest -q
python scripts/encoding_guard.py --all
```

Frontend / Tauri:

```powershell
cd admin-app
npm ci
npm run build
cd src-tauri
cargo check
```

## Notes

- Current repo had no refund API before M7. A minimal `POST /api/guests/{guest_id}/refund` flow was added to satisfy the M7 POS stub scope and tests.
