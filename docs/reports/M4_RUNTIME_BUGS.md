# M4 Runtime Bugs RCA (Postgres)

Date: 2026-02-25  
Branch: `m4/stabilize-runtime-sync`

## S1: "Sync passed", but no pours in `/api/pours`

Symptom:
- Controller logs looked successful after sync.
- Backend accepted sync request.
- New records did not appear in `/api/pours`.

Root cause:
- `rpi-controller` used `/api/guests` card lookup instead of `/api/visits/authorize-pour`.
- Backend `process_pour` treated late sync without active lock (`active_tap_id is None`) as `status="accepted"` with `late_sync_*`.
- Controller marked such records as `confirmed`, so local retry stopped, while backend only wrote audit.

Fix:
- Backend now returns explicit non-success `status="audit_only"` for late sync (`audit_late_matched`, `audit_late_recorded`).
- Controller treats `audit_only` as terminal non-success (`audit_only` local status), not normal success.
- Sync response includes explicit `outcome`.

How to verify:
1. Prepare active visit and tap, but do not call `authorize-pour`.
2. Send `/api/sync/pours`.
3. Expect `results[0].status == "audit_only"` and `outcome == "audit_late_recorded"` (or `audit_late_matched`).
4. Confirm no new matching entry in `/api/pours`.

## S2: Pour allowed when card is only bound in Guests (no active visit)

Symptom:
- Card linked to guest in Guests allowed physical pour start.
- Later sync failed due missing active visit.

Root cause:
- Controller authorization relied on card presence in `/api/guests`, not visit lock contract.
- Valve could open without successful backend `authorize-pour`.

Fix:
- Controller now requires `/api/visits/authorize-pour` before opening valve.
- If authorize fails (including no active visit), valve never opens and controller enters `CARD_MUST_BE_REMOVED`.
- Backend authorize rejection is explicitly logged with runtime diagnostics.

How to verify:
1. Bind card to guest, do not open visit.
2. Present card on reader.
3. Confirm authorize denial and no valve opening.

## S3: Brief valve opening after error/desync/block

Symptom:
- After reject/desync paths and with card still on reader, valve could briefly open again.

Root cause:
- Main loop immediately retried while card remained present.
- No hard "remove card first" state between failed attempts.

Fix:
- Added controller state `CARD_MUST_BE_REMOVED`.
- In this state valve is always forced closed.
- Exit requires card removal with debounce (`0.8s`) to avoid chatter.

How to verify:
1. Trigger authorize reject or sync-block path.
2. Keep card on reader.
3. Confirm controller stays blocked, valve closed.
4. Remove card and wait debounce; only then next attempt is possible.

## S4: Controller log spam

Symptom:
- Repeated `processing_sync` logs flooded terminal output.

Root cause:
- Loop logged the same message on every fast poll iteration.

Fix:
- Added throttled status logging in `FlowManager` and `SyncManager`.
- Kept key logs only: authorize allow/deny, session start/end, sync summary.

How to verify:
1. Leave unsynced record present.
2. Observe logs for 20+ seconds.
3. Confirm `processing_sync` appears throttled (not on every loop).

## Runtime diagnostics added

For `authorize-pour` and `/api/sync/pours`, logs now include:
- `request_id`,
- `db_identity` (`host:port/database`),
- `alembic_revision`,
- explicit `outcome` values (`pending_created`, `pending_exists`, `pending_updated_to_synced`, `audit_late_recorded`, `rejected_no_active_visit`, `rejected_tap_mismatch`, etc.).
