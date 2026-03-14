# TAP_DISPLAY_FOUNDATION_CORRECTIONS

Date: 2026-03-14
Scope: Priority 1 foundation corrections for the already-landed Tap Display implementation, plus small local Priority 2 kiosk hardening

## 1. Scope of corrections

This package corrects the foundation issues called out in `TAP_DISPLAY_FOUNDATION_ARCHITECTURE_AUDIT.md` without expanding Tap Display feature scope.

Included:

- narrow display-scoped auth for snapshot/media read access;
- explicit client state-precedence resolver and tests;
- MVP-safe media upload/content hardening;
- small Raspberry Pi kiosk startup hardening;
- targeted verification and correction report documentation.

Explicitly not included:

- new guest-facing screens or UI features;
- Admin App display settings expansion;
- media picker workflow;
- fleet management or production kiosk supervision;
- broad schema/migration redesign.

## 2. Auth boundary correction

### What was wrong

- `tap-display-agent` used the broad internal token path shared with controller traffic.
- `backend/security.get_current_user` accepted `X-Internal-Token`, so the internal device credential was valid across protected backend routes.
- The display path still relied on `demo-secret-key` compatibility if config hygiene was weak.

### What changed

- Backend now has three distinct auth paths:
  - `get_current_user`: operator/admin JWT only;
  - `get_internal_service_user`: explicit internal-token path for controller/internal routes;
  - `get_display_reader`: display-scoped read-only access for Tap Display snapshot/media reads.
- Display snapshot and media content routes now accept:
  - `X-Display-Token`, or
  - operator/admin JWT.
- Media upload and media list routes remain operator/admin JWT only.
- `tap-display-agent` now requires `DISPLAY_API_KEY` and sends `X-Display-Token` to backend.
- `tap-display-agent` no longer falls back to `INTERNAL_TOKEN`, `INTERNAL_API_KEY`, or `demo-secret-key`.
- Controller-facing routes that genuinely need internal access (`/api/visits/authorize-pour`, `/api/controllers/flow-events`) were moved onto the explicit internal dependency instead of the shared display/admin path.

### Why this is safer

- Browser still talks only to localhost agent and never receives backend credentials.
- Display-agent now has a narrower read-only credential with no write/admin scope.
- Display auth is no longer coupled to the controller credential path.
- Broad internal-token acceptance is no longer inherited by display/media routes.

## 3. Client state precedence fix

### Frozen precedence matrix

The display client now resolves state in this order:

1. `runtime_denied`
2. `controller_runtime_stale`
3. `runtime_blocked`
4. `bootstrap_missing_backend_lost`
5. `emergency_stop`
6. `tap_service_state`
7. `runtime_authorizing`
8. `runtime_authorized`
9. `runtime_pouring`
10. `runtime_finished`
11. `backend_link_lost`
12. `booting`
13. `idle`

### Behavioral fixes

- `controller_runtime_stale` now wins before branded active states, so stale `authorized` / `pouring` / `finished` sessions degrade to a service state instead of pretending to stay healthy.
- Tap statuses beyond `cleaning` are now explicitly mapped:
  - `locked`
  - `processing_sync`
  - `empty`
  - `cleaning`
- `emergency_stop` now wins over ordinary tap unavailability.
- Backend link loss still keeps local active session rendering for `authorized` / `pouring` / `finished`, but with a warning instead of silently hiding the degraded condition.

### Implementation notes

- Precedence logic was moved into `tap-display-client/src/display-state.js`.
- `App.svelte` now renders from the resolved state contract instead of carrying the precedence matrix inline.
- Node-based tests were added for the resolver.

## 4. Media hardening

### Added validation

- Allowed media kinds are explicitly limited to:
  - `background`
  - `logo`
- Allowed formats are explicitly limited to:
  - PNG
  - JPEG
- Declared MIME type must match the detected file signature.
- File extension must match the allowed extension set for the detected format.
- Empty uploads are rejected.
- Oversized uploads are rejected.
- Default upload size limit is `5 MiB` via `MEDIA_UPLOAD_MAX_BYTES`.

### Asset metadata policy

- `width` and `height` are now populated for supported PNG/JPEG uploads.
- The existing columns remain useful and are no longer "modeled but empty" for newly uploaded display assets.

### Error and lifecycle handling

- Upload writes are validated before persistence.
- If DB persistence fails after file save, the just-written file is deleted to avoid new orphan files from the failure path.
- Snapshot generation now drops missing assets instead of emitting broken display references.
- Media content endpoint returns a clear `404` when DB metadata exists but the file is missing.
- `tap-display-agent` now drops unavailable assets from the locally rewritten snapshot instead of letting a broken asset break the whole display snapshot render path.

### Deferred

- Full orphan/reference-count cleanup is still deferred as an operational task.
- Only the upload/content safety path was hardened in this package.

## 5. Kiosk/deployment hardening

### What improved

- `tap-display-kiosk.sh` now waits for local agent readiness before launching Chromium.
- Chromium is relaunched in a loop if it exits.
- `tap-display-agent.service` now starts after `beer-tap-controller.service`.
- Controller and agent services both pre-create `/run/beer-tap`.
- Pi deployment docs now document the required `DISPLAY_API_KEY`.

### What remains pilot-grade

- Chromium is still launched from desktop autostart rather than a dedicated supervised kiosk service.
- There is still no remote watchdog, screenshot telemetry, or fleet-level recovery tooling.
- Real on-device validation is still required before calling the kiosk path production-ready.

## 6. Tests and verification

Executed in this correction package:

- `python -m pytest backend/tests/test_tap_display_api.py backend/tests/test_security.py backend/tests/test_controller_flow_events.py backend/tests/test_incident_free_pour_zero_balance.py backend/tests/test_m3_tap_lock.py -q`
- `npm test` in `tap-display-client`
- `npm run build` in `tap-display-client`
- `python scripts/encoding_guard.py --all`

Covered scenarios:

- display snapshot read via display token;
- display token rejected on write path;
- internal token rejected on admin route but accepted on explicit internal route;
- stale-runtime precedence over active branded state;
- tap status service mapping for `locked`, `processing_sync`, and `empty`;
- media validation failures for invalid kind/MIME/extension;
- missing asset omitted from snapshot and returned as `404` on direct content access.

Verification note:

- `encoding_guard.py --all` now passes cleanly after targeted UTF-8 remediation of the branch-owned regressions in `backend/api/beverages.py`, `backend/api/taps.py`, and `tap-display-client/src/App.svelte`.

## 7. Encoding and repository health closure

### Audit result

The initial `python scripts/encoding_guard.py --all` audit failed on exactly 3 files:

- `backend/api/beverages.py`
- `backend/api/taps.py`
- `tap-display-client/src/App.svelte`

All 3 files overlap with the `master...foundation/tap-display-corrections` diff, so the failures were branch-local regressions inside the correction package rather than unrelated old repository debt.

### Attribution

- `backend/api/beverages.py` and `backend/api/taps.py` were part of the branch diff and were degraded while the Tap Display backend corrections were being landed; the earlier audit and blame pass tied that degradation to the branch-local work around commit `5ff4561`.
- `tap-display-client/src/App.svelte` was added by the branch itself and entered the branch in a mojibake state from commit `2b4785b`.

### What was fixed

- Restored the damaged Russian route summaries, docstrings, and comments in `backend/api/beverages.py` and `backend/api/taps.py` to valid UTF-8 without changing business logic.
- Normalized `tap-display-client/src/App.svelte` with a targeted `ftfy`-based repair and a follow-up sanity pass over user-facing strings.
- Fixed the remaining visible artifacts that required manual follow-up after `ftfy`:
  - ruble symbol formatting;
  - `мл` volume unit;
  - `Сумма` labels;
  - the corrupted idle separator;
  - remaining escaped display-copy literals so the final file contains normal UTF-8 text.

### Final health status

- `python scripts/encoding_guard.py --all` is green.
- No encoding issues remain in the current branch diff.
- No independent repository-wide encoding cleanup is required to merge this correction package.

### Merge impact

Encoding and repository health no longer block the branch. The correction package now closes its own obvious encoding regressions instead of carrying them forward as documented debt.

## 8. Remaining non-blocking debt

- `sync_pours` auth contract was intentionally left untouched to avoid widening scope beyond Tap Display corrections.
- Display auth is environment-key scoped, not yet device-registry scoped.
- DB-level enum/check constraints for display fields are still deferred.
- Full asset orphan cleanup/reference tracking is still deferred.
- Kiosk supervision is improved but still pilot-grade.

## 9. Final verdict

Yes.

The Tap Display foundation is now materially safer to continue building on:

- display-agent uses a narrower read-only auth path;
- stale/runtime/service precedence is explicit and test-backed;
- media upload/content handling is hardened to an MVP-safe state;
- kiosk startup is more resilient for pilot use;
- branch-owned encoding regressions are closed and `encoding_guard` is green.

Tap Display feature development can continue on top of this corrected foundation, with the remaining items above treated as non-blocking follow-up debt rather than release-blocking foundation flaws.
