# TAP_DISPLAY_FOUNDATION_MERGE_READINESS

Date: 2026-03-14
Branch: `foundation/tap-display-corrections`
Base: `master`

## 1. Scope

This merge-readiness pass covers the Tap Display foundation correction package only:

- auth boundary narrowing for display snapshot/media reads;
- display client precedence-matrix correction;
- media upload/content hardening;
- kiosk startup resilience improvements;
- encoding and repository health closure for branch-owned regressions.

Out of scope:

- new Tap Display features;
- Admin App display management expansion;
- unrelated refactors or repo-wide debt cleanup outside the branch overlap.

## 2. What was fixed

### Auth boundary

- Display snapshot/media read routes now use the display-scoped read dependency instead of inheriting the broad internal-token path.
- Internal token access remains explicit for controller/internal routes only.
- Security tests confirm internal tokens are rejected on admin routes and accepted only where intended.

### Precedence matrix

- Display state precedence is now centralized in `tap-display-client/src/display-state.js`.
- The stale-runtime case now wins over branded active states.
- Explicit service-state mapping exists for `locked`, `processing_sync`, `empty`, and `cleaning`.
- Display-client tests cover the frozen precedence order and key degraded-state scenarios.

### Media hardening

- Media uploads now validate kind, signature, MIME type, extension, emptiness, and file size.
- Snapshot generation omits missing assets instead of returning broken references.
- Direct media content requests return `404` when metadata exists but the file is missing.
- Backend tests cover invalid media input and missing-asset behavior.

### Kiosk hardening

- The kiosk launcher waits for local agent readiness before opening Chromium.
- Chromium is relaunched in a loop if it exits.
- The tap-display-agent service starts after the controller service.
- Both controller and agent services pre-create `/run/beer-tap`.

### Encoding and repository health closure

- `python scripts/encoding_guard.py --all` initially failed on exactly 3 files:
  - `backend/api/beverages.py`
  - `backend/api/taps.py`
  - `tap-display-client/src/App.svelte`
- All 3 files are part of the branch diff, so the failure belonged to this branch and could not be documented away as independent old debt.
- `backend/api/beverages.py` and `backend/api/taps.py` were restored to valid UTF-8 without business-logic changes.
- `tap-display-client/src/App.svelte` was normalized with a targeted `ftfy` repair plus a manual sanity pass over user-facing strings.
- The final branch state is green under `encoding_guard`.

## 3. Remaining known issues

The following items remain but do not block merging this correction package:

- `sync_pours` auth contract was intentionally left untouched to avoid widening scope.
- Display auth is environment-key scoped, not yet device-registry scoped.
- DB-level enum/check constraints for display fields are still deferred.
- Full asset orphan cleanup/reference tracking is still deferred.
- Kiosk supervision is improved but still pilot-grade rather than production-grade.

No remaining encoding issue is carried by this branch.

## 4. Verification results

### Backend tests

- Command:
  - `python -m pytest backend/tests/test_tap_display_api.py backend/tests/test_security.py backend/tests/test_controller_flow_events.py backend/tests/test_incident_free_pour_zero_balance.py backend/tests/test_m3_tap_lock.py -q`
- Result:
  - `22 passed, 7 warnings`

### Display client tests

- Command:
  - `npm test`
- Result:
  - `6` tests passed

### Display client build

- Command:
  - `npm run build`
- Result:
  - production build completed successfully with Vite

### Encoding guard

- Command:
  - `python scripts/encoding_guard.py --all`
- Result:
  - `OK: no UTF-8/mojibake/bidi-control issues found.`

### Focused foundation sanity status

- Auth boundary isolation is consistent with route dependencies and `backend/tests/test_security.py`.
- Precedence matrix behavior is covered by `tap-display-client/test/display-state.test.js`.
- Media validation is covered by `backend/tests/test_tap_display_api.py`.
- Kiosk hardening changes remain limited and did not break build or test verification.

## 5. Final verdict

`READY TO MERGE`

Why:

- the branch closes its own obvious encoding defects instead of carrying them forward;
- `encoding_guard` is green;
- backend verification is green;
- display client tests and build are green;
- no remaining blocker was found inside the correction-package scope.
