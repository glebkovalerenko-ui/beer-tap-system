# TAP_DISPLAY_ON_DEVICE_SMOKE_AND_PILOT_READINESS

Date: 2026-03-14

## 1. Scope

This phase checked Tap Display system viability as a device-facing chain, not as a new feature sprint.

Covered in this phase:

- backend snapshot/media contract correctness
- agent polling, `ETag`, asset caching, and runtime bridge
- controller runtime publication and display-state precedence
- display client state handling and build readiness
- Raspberry Pi bring-up documentation and kiosk startup path audit

Not added in this phase:

- new product features
- new architecture
- offline mode
- fleet tooling
- simulator expansion
- unrelated cleanup

## 2. Environment

### Actual execution environment in this session

- Windows workstation checkout at `c:\Users\CatNip420\Documents\Projects\beer-tap-system`
- Python test environment from the current workstation
- Node/Vite environment from the current workstation

### Intended target environment

- Raspberry Pi local checkout at `/opt/beer-tap-system`
- Chromium kiosk pointing at `http://127.0.0.1:18181/display/`
- `beer-tap-controller.service`
- `tap-display-agent.service`
- `/run/beer-tap/display-runtime.json`
- `/etc/beer-tap/device.env`

### Important limitation

Actual Raspberry Pi / monitor execution was not available from this session. Because of that, this report separates:

- software-only verification completed in this repo
- deployment/runtime path audited from artifacts
- final hardware-only checks still required on the Pi

## 3. Smoke matrix

| State | Expected behavior | Actual behavior | Result | Notes |
| --- | --- | --- | --- | --- |
| idle | Assigned beverage, branded idle content, price/instruction visible | Snapshot contract, price/copy/theme wiring verified in backend tests; display client idle path builds and resolves copy correctly | PASS (software-only) | Not visually confirmed on Pi in this session |
| no keg / unavailable | Guest-safe fallback message, no blank screen | Service-state mapping for `no_keg` / `empty` remains present in client logic and build passes | PASS (software-only) | Needs final device readability check |
| authorized | Guest name/balance/readiness visible | Controller runtime publication for authorized path already covered by `rpi-controller/test_flow_manager.py`; client precedence keeps runtime over branded idle | PASS (software-only) | No live card swipe on Pi in this session |
| denied | Clear deny reason, no broken layout | Denied runtime path remains covered by controller tests; client deny mapping remains stable | PASS (software-only) | No physical render confirmation |
| pouring | Live volume/cost/remaining balance updates | Controller runtime publish path is covered by controller tests; agent runtime bridge is covered by new `tap-display-agent/test_service.py` | PASS (software-only) | No physical flow meter session executed here |
| finished | Final totals shown, then clean return path | Finished runtime summary remains covered by controller tests; client finished state builds cleanly | PASS (software-only) | Completion window still needs a Pi observation pass |
| backend unavailable / degraded | No silent blank screen; explicit degraded state | Client `no_connection` / warning precedence remains covered by display-state tests; agent backend-loss tracking remains unchanged | PASS (software-only) | Needs a real Pi network-drop smoke |
| processing sync / blocked-like | Clear service state while unsynced work exists | Controller processing-sync block path is already covered by runtime tests; client service mapping remains stable | PASS (software-only) | Needs a real unsynced-on-device repro |

## 4. Wiring verification

### Admin App -> backend

- Backend display workflow contract remains verified by `backend/tests/test_tap_display_api.py`.
- Media upload, beverage display edits, tap display config edits, and effective snapshot generation still pass.
- The wire contract bug found in this phase was real: backend returned `copy_block` on the wire while the spec/client expected `copy`.
- Fixed in this phase so the snapshot now serializes `copy` on the wire.

### Backend -> tap-display-agent

- Added `tap-display-agent/test_service.py` to verify:
- snapshot poll
- `If-None-Match` reuse
- `ETag` persistence
- asset download and local cache rewrite
- runtime file bridge
- This confirms the agent can consume the corrected snapshot contract and keep serving local asset URLs.

### Controller runtime -> display-agent / display-client

- Existing `rpi-controller/test_flow_manager.py` confirms idle, denied, authorized, pouring, and finished runtime publication behavior.
- Existing `backend/tests/test_controller_flow_events.py` confirms controller/backend flow-event integration remains healthy.
- No runtime contract change was required in this phase.

### Display client on device

- `tap-display-client` tests and build pass.
- Added rollout-safe compatibility so the client accepts both:
- `snapshot.copy`
- legacy `snapshot.copy_block`
- This avoids pilot breakage if a cached/older payload is still present during transition.

## 5. UX/readability findings

Findings from this phase were limited because no physical monitor/Pi render was available in-session.

Confirmed:

- idle/service/authorized/pouring/finished state codepaths remain compact and dedicated, not debug-page style
- service states still suppress branded idle presentation where appropriate
- the corrected copy contract prevents missing fallback/maintenance copy on the screen

Still requires real-device check:

- numeric readability at real viewing distance
- background/text contrast on the target monitor
- final size/readability of price, balance, and volume
- completion window feel and idle return timing

No broad UX rewrite was made. Only safe pilot-readiness compatibility and contract fixes were applied.

## 6. Deployment / kiosk findings

Already good enough for pilot-oriented bring-up:

- separate controller and display-agent services exist
- display agent waits on backend polling rather than coupling the browser to backend auth
- kiosk launcher waits for local agent health
- kiosk launcher relaunches Chromium if it exits

Still pilot-grade / not fully proven in this session:

- Chromium autostart is desktop-session based, not a supervised service
- no live Pi boot/reboot observation was performed here
- no live `systemd` restart/recovery behavior was observed from hardware
- no real network-loss/kiosk-recovery pass was executed on Pi from this environment

Improvement made in this phase:

- `deploy/rpi/README.md` now gives a concrete, reproducible Pi bring-up flow with build/install/enable/check commands and kiosk smoke steps

## 7. Fixes made in this phase

1. Fixed display snapshot wire serialization so the API now emits `copy` instead of the internal `copy_block` name.
2. Updated backend tests to assert the real wire contract and reject `copy_block` in the serialized snapshot.
3. Added display-client compatibility fallback for legacy `copy_block` payloads during rollout/cache transition.
4. Added a focused display-agent smoke test covering polling, `ETag`, cached assets, local asset URL rewrite, and runtime bridge.
5. Expanded Raspberry Pi deployment documentation with an explicit bring-up and smoke checklist.

## 8. Remaining non-blocking limitations

- Actual Raspberry Pi hardware smoke is still required before claiming full demo readiness.
- Admin App content propagation was re-verified at backend API contract level in this session, not through an interactive live Admin UI run.
- Kiosk/session behavior after real boot, login, backend loss, and Chromium crash still needs a final Pi pass.
- `systemd-analyze verify` and on-device shell syntax checks were not run here because the touched deployment artifact was documentation, not the unit/script files themselves.

## 9. Final verdict

`MOSTLY READY, NEEDS SMALL FOLLOW-UP`

Why:

- the main pilot-blocking wiring bug in the display content contract was fixed
- backend, controller, agent, and display client software paths are now re-verified together at contract/test level
- deployment guidance is clearer and more reproducible
- but a final honest Raspberry Pi / monitor smoke pass is still required to confirm kiosk startup, physical readability, and degraded-state behavior on the actual device
