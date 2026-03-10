# M7 Verification

Date: 2026-03-04
Status: historical M7 verification record

## Scope

- FIFO keg suggestion endpoint
- admin-app FIFO hint in keg assignment flow
- POS stub notifications for top-up, refund, and finalized pours

## Verified implementation decisions

- no new keg timestamp column was added
- FIFO uses existing `kegs.created_at`
- current schema uses `beverage_id` as the practical equivalent of `beer_type_id`
- eligible FIFO stock is:
  - same `beverage_id`
  - `status = full`
  - `current_volume_ml > 0`
  - not assigned to any tap
- deterministic ordering is:
  - `created_at ASC`
  - `keg_id ASC`

## Expected FIFO behavior

- recommendation only, no automatic assignment
- operator can still override the suggested keg
- API response includes candidate count and ordering keys used

## Expected POS stub behavior

- top-up emits one stub event per transaction
- refund emits one stub event per transaction
- finalized pour emits one stub event per logical pour
- duplicate sync or late sync after reconcile does not emit a second pour event

## Related current docs

- `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`
- `docs/API_REFERENCE.md`
- `docs/reports/STAGE_COMPLETION_VERDICT_PRE_NEXT_PHASE.md`
