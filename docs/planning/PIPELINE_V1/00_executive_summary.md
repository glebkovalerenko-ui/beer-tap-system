# Executive Summary — Pipeline V1

## Is the repo currently aligned with `OPERATIONAL_MODEL_V1`?
- **Not yet.** The repo has strong foundations (guest/card/tap/keg/pour sync, emergency stop, audit, offline local journal), but several core operational-model primitives are absent: Visit, LostCard registry, Alert lifecycle, backend Shift model/wizard, explicit sync-status/tap-processing semantics, and POSAdapter boundary.

## Biggest gaps
1. **Missing Visit aggregate** (and therefore missing active visit invariants + `active_tap_id` lock semantics).
2. **Missing Alert and LostCard domain models** (critical for incident and security workflows).
3. **Missing backend Shift lifecycle + closure gates** (current shift logic is local UI state only).
4. **Partial offline-sync semantics** (local queue exists, but no explicit backend `pending_sync/synced` and no `processing_sync` behavior).
5. **No explicit POSAdapter contract implementation boundary.**

## Recommended milestone sequence
1. Domain schema alignment (additive, backward-compatible).
2. Visit lifecycle and invariants.
3. Pour sync-state + `processing_sync` tap semantics.
4. Active tap lock and simultaneous-use prevention.
5. LostCard registry + enforcement.
6. Keg lifecycle alignment + FIFO recommendation.
7. Alert severity + acknowledge/resolve workflows.
8. Shift backend model + closure wizard/reporting.
9. POSAdapter boundary in MVP stub/manual mode.

## Top 3 highest-risk items to tackle early
1. **Visit + active lock correctness** (prevents misuse and race conditions).
2. **Offline reconciliation correctness** (`pending_sync`, lock release, mismatch handling).
3. **Schema migration strategy** (currently no tracked alembic versions; needs disciplined rollout).

## What can be safely deferred
- Deep POS integration (beyond adapter contract + stub mode).
- Multi-location operational features (retain schema readiness only).
- Advanced role hierarchy enforcement (keep unified staff role for MVP).
- Advanced card cryptography and sensor-heavy keg automation.
