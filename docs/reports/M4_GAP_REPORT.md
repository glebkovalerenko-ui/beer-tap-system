# M4 Gap Report

## Scope
This report checks M4 requirements from `docs/planning/PIPELINE_V1/07_demo_oriented_pipeline.md` against the current branch state (`m4-offline-sync-reconcile`).

## A) M4 Checklist (Done / Not Done)

| Requirement | Implemented? | Where in code | How to verify |
|---|---|---|---|
| `pours.sync_status` model with deterministic states (`pending_sync` / `synced` / `reconciled`) | no (partial) | `backend/alembic/versions/0004_m4_offline_sync_reconcile.py`; `backend/models.py`; `backend/crud/pour_crud.py`; `backend/crud/visit_crud.py` | Run `pytest backend/tests/test_m4_offline_sync_reconcile.py`. Column and constraints exist, `synced` and `reconciled` are used, but there is no runtime path that persists `pending_sync`. |
| Tap domain includes `processing_sync` and blocks normal flow until resolution | yes | `backend/crud/visit_crud.py` (`authorize_pour_lock`, `reconcile_pour`, `force_unlock_visit`, `close_visit`); `backend/crud/pour_crud.py` | `test_lock_kept_until_backend_accepts_sync` in `backend/tests/test_m4_offline_sync_reconcile.py` plus manual API flow (`authorize-pour` then `sync`). |
| Lock clear rules: `active_tap_id` and `lock_set_at` clear only on accepted sync / manual reconcile (or explicit admin paths) | yes | `backend/crud/pour_crud.py` (accepted sync), `backend/crud/visit_crud.py` (`reconcile_pour`, `force_unlock_visit`, `close_visit`) | `test_lock_kept_until_backend_accepts_sync`, `test_manual_reconcile_unlocks_visit_and_is_idempotent` (`backend/tests/test_m4_offline_sync_reconcile.py`). |
| Manual reconcile path for timeout cases | yes | `POST /api/visits/{visit_id}/reconcile-pour` in `backend/api/visits.py`; implementation in `backend/crud/visit_crud.py` | `test_manual_reconcile_unlocks_visit_and_is_idempotent` (`backend/tests/test_m4_offline_sync_reconcile.py`). |
| Late sync handling with match / mismatch after manual reconcile, no second charge | yes | `backend/crud/pour_crud.py` (`late_sync_matched`, `late_sync_mismatch`) | `test_late_sync_after_manual_reconcile_match_and_mismatch_no_double_charge` (`backend/tests/test_m4_offline_sync_reconcile.py`). |
| Minimal review event for mismatch | yes | Audit log write in `backend/crud/pour_crud.py` (`action="late_sync_mismatch"`) | Check `/api/audit/` after mismatch; covered by `test_late_sync_after_manual_reconcile_match_and_mismatch_no_double_charge`. |

## Not fully implemented
- `pours.sync_status = pending_sync` has schema/constraints support, but no runtime persistence path currently writes `pending_sync`; active paths use `synced` and `reconciled`.

## B) Follow-up Issue Card: "Open visit and issue card"

Target button flow: `Read NFC UID -> bind card to guest (if needed) -> assign card to visit -> UI confirmation`.

### Backend tasks
1. Add endpoint `POST /api/visits/open-and-assign-card` (or orchestrate in service layer) that performs open/bind/assign atomically in one DB transaction.
2. Reuse current rules from `POST /api/guests/{guest_id}/cards` and `POST /api/visits/{visit_id}/assign-card` to avoid duplicate business logic.
3. Return structured result with operation stage (`bound`, `already_bound`, `assigned`) and explicit conflict reasons for UI.
4. Add idempotency key support for operator double-click/retry safety.

### Admin-app tasks
1. Add operator action button: "Open visit and issue card".
2. Use NFC store value (`uid`) as input; disable button when UID missing.
3. Show deterministic result states: success, bind conflict, card busy, visit already active.
4. Log operation result in activity panel for traceability.

### Controller tasks
1. Expose stable NFC read event contract (UID + read timestamp + reader id).
2. Ensure duplicate NFC reads are de-bounced before sending to UI workflow.
3. Provide explicit "card removed" signal so UI can reset CTA state.

### Pipeline placement
Proposed dedicated milestone: **M3.6 - Visit Open + Card Issue Operator Flow**.
- Why here: this is a visit orchestration UX/transaction gap, independent from M4 offline sync semantics.
- Exit criteria: single-click operator flow works end-to-end with deterministic conflict messaging and idempotent retries.

## How to verify (operator)
1. Log in as admin, create two guests (A and B), create a beverage/keg/tap, top up guest A, and bind one card UID to guest A via `POST /api/guests/{guest_id}/cards`.
2. Open a visit for guest A with that card (`POST /api/visits/open`) and authorize pour on the prepared tap (`POST /api/visits/authorize-pour`).
3. Confirm the visit is locked for sync: `active_tap_id` equals tap id and `lock_set_at` is not null (also visible via `GET /api/visits/active/by-card/{card_uid}`).
4. Reproduce offline timeout by not sending controller sync (`POST /api/sync/pours`) and waiting for the operator timeout decision point.
5. Run manual reconcile: `POST /api/visits/{visit_id}/reconcile-pour` with `reason=sync_timeout`, `tap_id`, `short_id`, `volume_ml`, and `amount`; verify response clears lock (`active_tap_id=null`).
6. Repeat the same reconcile request once more and verify idempotency: still `200`, still unlocked, and only one pour record with that `short_id`, `sync_status=reconciled`, `is_manual_reconcile=true`.
7. Close the visit with card return flag: `POST /api/visits/{visit_id}/close` and payload `{ "closed_reason": "checkout", "card_returned": true }`.
8. Verify card release by binding and assigning the same card UID to guest B in a new visit (`POST /api/guests/{guest_b}/cards` + `POST /api/visits/{visit_b}/assign-card`); both operations must return `200`.
