# ZERO-VOLUME Pending Sync Fix Option B

## 1. Problem statement

The stuck `processing_sync` incident came from a backend-side contract mismatch:

- backend created a durable `pending_sync` row during `POST /api/visits/authorize-pour`
- controller created a local sync artifact only after a factual pour with `total_volume_ml > 1`
- zero-volume authorize-abort therefore left backend `pending_sync`, `taps.status='processing_sync'`, and `visits.active_tap_id/lock_set_at` without a normal completion signal

That made the Tap Display snapshot honestly stay in `processing_sync`, even though the controller runtime was already idle.

## 2. Previous contract

Before this fix the lifecycle was:

1. `authorize-pour` in `backend/crud/visit_crud.py` set `visit.active_tap_id`, `visit.lock_set_at`, switched `tap.status` to `processing_sync`, and created/reused a durable backend `pending_sync` row.
2. Controller completed the hardware session in `rpi-controller/flow_manager.py`.
3. Controller wrote a local journal record only when `total_volume_ml > 1`.
4. Sync worker later sent `/api/sync/pours`.
5. Backend finalized the existing pending row to `synced` or `rejected`, then cleared lock/tap state.

Why zero-volume broke:

- authorize created durable backend state before any factual pour artifact existed
- zero-volume abort created no local journal row
- no `/api/sync/pours` payload could ever be sent
- backend had no normal event to terminate the pending row or clear `processing_sync`

## 3. New contract

The new contract splits the lifecycle into lock stage and durable sync stage.

### Authorize stage

`POST /api/visits/authorize-pour` now only:

- validates shift/card/visit/tap/clamp policy
- sets `visit.active_tap_id`
- sets `visit.lock_set_at`

It no longer creates durable `pending_sync` and no longer moves the backend tap to `processing_sync`.

### Durable sync start

The durable sync lifecycle now starts when the controller has already persisted a real local pour artifact:

1. Controller finishes a factual pour with `total_volume_ml > 1`.
2. Controller writes the local journal row first via `db_handler.add_pour(...)`.
3. Immediately after that it calls new internal backend endpoint:
   - `POST /api/visits/register-pending-pour`
4. Backend creates or refreshes one durable `pending_sync` row and moves the tap to `processing_sync`.
5. Later `/api/sync/pours` finalizes that pending row to `synced` or `rejected`.

### Zero-volume exit

If the session ends without a real pour artifact (`total_volume_ml <= 1`), controller calls:

- `POST /api/visits/release-pour-lock`

Backend then clears:

- `visit.active_tap_id`
- `visit.lock_set_at`

without creating any durable `pending_sync`.

### Safety net

`/api/sync/pours` now also backfills a missing pending row when:

- the visit is still actively locked on the same tap, and
- a factual sync payload arrives

This is a resilience fallback, not the primary contract point.

## 4. Why Option B was chosen

Option B was implemented at the local-journal creation point, not at first flow pulse and not only at final sync.

Why this point is correct:

- It is the first point where a durable controller-side pour artifact definitely exists.
- Volume, duration, short ID, and authorized price snapshot are already known.
- The backend durable state no longer gets ahead of the controller durable state.
- It preserves backend-side `pending_sync` visibility during the unsynced interval for real pours.
- It avoids using flow-events as the source of truth, because flow-events are telemetry, not the controller durable journal.
- It is better than "create only on final sync", because that would hide the pending interval from backend operational state.

## 5. Zero-volume path after fix

After the fix, a zero-volume authorize-abort path is:

1. Controller authorizes successfully and receives lock/clamp data.
2. No factual pour artifact is created because `total_volume_ml <= 1`.
3. Controller does not write a local journal row.
4. Controller calls `release-pour-lock`.
5. Backend clears the active tap lock.
6. No durable `pending_sync` row exists.
7. Backend tap status stays `active`, so display snapshot cannot get stuck in `processing_sync` from this path.

Result:

- no orphaned backend sync row
- no stuck backend `processing_sync`
- no normal-path dependence on a nonexistent local sync payload

## 6. Non-zero pour path after fix

After the fix, a real pour path is:

1. Controller authorizes and backend sets only the visit lock.
2. Controller measures real flow and ends the session.
3. If `total_volume_ml > 1`, controller writes the local journal row.
4. Controller registers durable pending on backend.
5. Backend creates one `pending_sync` row for that visit/tap and switches tap status to `processing_sync`.
6. Sync worker sends `/api/sync/pours`.
7. Backend finalizes the same pending row to:
   - `synced`, or
   - `rejected`
8. Backend clears lock and returns tap status to `active` unless keg became empty.

Recovery/manual paths remain intact:

- manual reconcile still works with or without an existing pending row
- late sync after manual reconcile is still audit-only
- if pending registration was missed, sync can backfill it while the lock is still active

## 7. Timeout-stop analysis

### How timeout-stop actually works now

The timer stop is implemented in `rpi-controller/flow_manager.py`, not in backend authorize windows and not in a separate valve/session manager.

Actual mechanics:

- constant: `FLOW_TIMEOUT_SECONDS = 15.0`
- trigger: inside the active pour loop, if `now - last_flow_at >= FLOW_TIMEOUT_SECONDS`
- scope: this is a no-flow inactivity timeout after authorize, while the card is still present
- post-close handling:
  - controller closes the valve
  - collects tail flow with `FLOW_TAIL_IDLE_SECONDS = 0.5`
  - stops tail collection at `FLOW_TAIL_MAX_SECONDS = 3.0`

This means the timeout behavior is a controller-level no-flow stop, not:

- an authorize validity window
- a backend timer
- a separate visit timeout daemon

### How timeout-stop interacts with the new contract

The new contract does affect timeout-stop, because timeout may end either with zero volume or non-zero volume.

#### Timeout with non-zero volume

If timeout happens after real flow and final `total_volume_ml > 1`:

- controller writes the local journal row
- controller registers backend `pending_sync`
- sync lifecycle continues normally

#### Timeout with zero volume

If timeout happens before any real pour artifact (`total_volume_ml <= 1`):

- controller does not create a local journal row
- controller calls `release-pour-lock`
- backend clears the lock without creating durable `pending_sync`

### Were code changes required?

Yes.

Required changes were:

- zero-volume timeout must now explicitly release the backend authorize lock
- non-zero timeout must use the same pending-registration point as any other factual pour

### Why the new scheme does not break timeout-stop

Because timeout-stop already branched naturally on factual poured volume:

- real factual pour -> local artifact exists -> durable pending is appropriate
- zero/near-zero abort -> no local artifact exists -> durable pending is not appropriate

The new contract now matches that real runtime split.

## 8. Tests and verification

Added or updated verification covered:

- zero-volume authorize-abort
  - backend `pending_sync` is not created on authorize
  - zero-volume release clears `active_tap_id` / `lock_set_at`
  - backend tap remains `active`
- normal non-zero pour
  - durable pending is created only after `register-pending-pour`
  - `/api/sync/pours` still finalizes the same row to `synced`
- regression/self-heal
  - sync can backfill missing pending when a real active lock still exists
- shift/report/flow integration
  - close-shift blocking still works when a real pending exists
  - flow-event sale paths still end in one final pour row
- timeout-stop
  - controller timeout with non-zero volume registers pending
  - controller timeout with zero volume releases lock and does not register pending

Executed checks:

- `python -m pytest backend/tests/test_m4_offline_sync_reconcile.py backend/tests/test_m6_insufficient_funds_clamp.py backend/tests/test_m5_shift_operational_mode.py backend/tests/test_m5_shift_reports_v1.py backend/tests/test_controller_flow_events.py backend/tests/test_incident_free_pour_zero_balance.py`
- `python -m pytest backend/tests/test_m3_tap_lock.py backend/tests/test_m7_fifo_pos_stub.py`
- `python -m pytest rpi-controller/test_flow_manager.py`
- `python scripts/encoding_guard.py --all`

Confirmed by tests:

- zero-volume durable stuck row from the RCA path is no longer produced
- normal real pours still finalize correctly
- timeout-stop now follows the right branch for zero-volume vs non-zero sessions

## 9. Remaining limitations

- Zero-volume lock release is now explicit, but it is still a controller-to-backend call rather than a locally persisted retry queue.
- If backend is unreachable exactly during that no-pour release call, the durable stuck `pending_sync` bug still does not recur, but the visit lock may require a later retry or operator recovery.
- Historical architecture docs still describe the old authorize-created pending contract; this report is the current contract reference for this fix.

## 10. Final verdict

`BUG FIXED, SMALL FOLLOW-UP REMAINS`
