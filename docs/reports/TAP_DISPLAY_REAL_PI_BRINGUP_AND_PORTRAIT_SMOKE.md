# Tap Display Real Pi Bring-up And Portrait Smoke

## 1. Scope

This work covered the real pilot bring-up of Tap Display on the Raspberry Pi controller, not a new feature sprint.

Completed scope:

- audited the live Raspberry Pi and `cybeer-hub` state before repair
- fixed backend reachability for the Pi pilot path
- repaired the stale backend deployment on `cybeer-hub`
- brought up `beer-tap-controller`, `tap-display-agent`, and Chromium kiosk on-device
- enabled portrait kiosk behavior for the real HDMI monitor
- ran pilot smoke checks for runtime, cached content, and degraded backend behavior

## 2. Environment

- Working branch: `feature/tap-display-real-pi-bringup`
- Branch base: `feature/tap-display-device-smoke`
- Base-branch reason: `feature/tap-display-admin-mvp` is not merged into `master`, while `feature/tap-display-device-smoke` already contains the Tap Display MVP state needed for this bring-up
- Raspberry Pi: `Raspberry Pi 3 Model B Plus Rev 1.4`
- Pi OS/runtime: Debian 13 (`Linux cybeer-00 6.12.47+rpt-rpi-v8 aarch64`)
- Pi repo path: `/home/cybeer/beer-tap-system`
- Hub repo path: `/home/cybeer/beer-tap-system`
- Hub address: `192.168.0.110`
- Pi address: `192.168.0.114`
- Physical monitor: `Dell U2713HM` over `HDMI-A-1`
- Display mode during bring-up: `1920x1080 @ 60 Hz`, portrait via compositor transform `90`
- Pilot network assumption: Pi-specific runtime config may override the repo hostname default when `cybeer-hub` is not resolvable on the device

## 3. Backend Reachability Fix

### What was broken

- The Raspberry Pi could not reliably reach the backend via `http://cybeer-hub:8000`.
- Controller and display flows needed stable backend access for status, snapshot, and display-config requests.
- The live `cybeer-hub` checkout was also stale and broken:
  - `.git` was an empty directory, so the checkout was not a working git repo
  - sync-conflict files were still present
  - `backend/api/display.py` was missing
  - live OpenAPI did not expose Tap Display routes
  - PostgreSQL did not yet have Tap Display tables

### Chosen fix

- For the Raspberry Pi pilot path, backend reachability was fixed by setting `SERVER_URL=http://192.168.0.110:8000` in `/etc/beer-tap/device.env`.
- `/etc/hosts` was not chosen for this stage.

### Why this was the best pilot option

- It is the smallest reliable change for one known pilot device.
- It does not alter repo-wide hostname defaults or broader architecture.
- It avoids relying on a cloud-init-managed `/etc/hosts` file on the Pi.
- It keeps the workaround isolated to the Pi runtime config until hostname resolution is addressed more globally.

### Hub repair decision

- Existing `cybeer-hub` checkout was audited before any destructive action.
- Safe in-place repair was rejected because the checkout was not a functioning git repo and already mixed with conflict debris.
- A timestamped backup was created first:
  - checkout backup: `/home/cybeer/beer-tap-system.backup-20260315-181630`
  - runtime env backup: `/home/cybeer/beer-tap-system.env.backup-20260315-181630`
- After backup, the checkout was replaced with a clean clone of `feature/tap-display-real-pi-bringup`, the existing runtime `.env` was restored, `DISPLAY_API_KEY` was added, and `docker compose up -d --build` was executed.

### Result

- `cybeer-hub` now serves the expected Tap Display backend routes:
  - `/api/display/taps/{tap_id}/snapshot`
  - `/api/taps/{tap_id}/display-config`
- Backend migrations reached `0014_tap_display_system`
- Display tables now exist in PostgreSQL:
  - `media_assets`
  - `tap_display_configs`
- The snapshot endpoint returns live content on the hub and on the Pi through the display agent

## 4. Runtime Bring-up

### Controller service

- `beer-tap-controller.service` is active on the Pi
- The controller is using the Pi-local pilot backend URL override
- Runtime snapshots are published to `/run/beer-tap/display-runtime.json`
- Current idle runtime was confirmed through `/local/display/runtime`

### Display agent

- `tap-display-agent.service` is active on the Pi
- The agent uses `DISPLAY_API_KEY` for read-only display snapshot access
- Confirmed local endpoints:
  - `GET http://127.0.0.1:18181/health`
  - `GET http://127.0.0.1:18181/local/display/bootstrap`
  - `GET http://127.0.0.1:18181/local/display/runtime`
- `bootstrap` now returns real backend content for Tap 1, including tap name, beverage name, branding, price text, and display copy

### Kiosk path

- LightDM autologin is enabled for user `cybeer`
- Session type is `labwc`
- Kiosk boot path is:
  - `lightdm autologin`
  - `labwc session`
  - `~/.config/labwc/autostart`
  - `/home/cybeer/beer-tap-system/deploy/rpi/tap-display-kiosk.sh`
  - Chromium kiosk at `http://127.0.0.1:18181/display/`
- The launcher waits for local agent health before opening Chromium
- Chromium is relaunched if it exits

## 5. Portrait Orientation Handling

### Selected implementation

- Portrait was implemented at the compositor/output layer, not in CSS and not through a browser-only rotation hack.
- `tap-display-kiosk.sh` applies `wlr-randr --output HDMI-A-1 --transform 90` before Chromium launch and on relaunch.

### Why this was chosen

- It keeps the whole session in the real physical orientation of the monitor.
- It avoids sideways Chromium or CSS-only rotation hacks.
- It is the simplest maintainable option for the pilot kiosk path.

### Real-device startup correction

- `~/.config/autostart/tap-display-kiosk.desktop` was not reliable enough for this `labwc` session.
- The stable pilot fix is explicit `labwc` autostart:
  - deploy artifact added: `deploy/rpi/labwc-autostart`
  - live Pi session now uses `~/.config/labwc/autostart`
- After switching to `labwc` autostart, repeated `lightdm` restarts still relaunched Chromium and preserved portrait rotation.

### UI tweaks

- No Tap Display client layout changes were required for the current portrait bring-up.
- Existing UI remained readable enough for the pilot idle/content path once the session itself was truly portrait.

## 6. Smoke Results

### Confirmed on the Pi

- `beer-tap-controller.service` is active
- `tap-display-agent.service` is active
- `lightdm` autologin session is active
- local agent endpoints respond successfully
- Tap Display content is fetched from the backend and exposed locally through the agent
- current idle runtime is present and fresh
- Chromium kiosk autostarts after `lightdm` restart without manual intervention
- compositor transform stays at `HDMI-A-1 -> 90`, matching the portrait monitor
- degraded backend behavior was exercised:
  - backend container was stopped briefly on `cybeer-hub`
  - Pi agent flipped to `backend_link_lost=true`
  - cached `/local/display/bootstrap` and `/local/display/runtime` still responded
  - backend recovery returned the agent to `backend_link_lost=false`

### Confirmed partially

- Idle/content state is strongly confirmed by live runtime, live cached snapshot, running Chromium kiosk, and portrait output transform, but still benefits from a final human glance at the physical panel for readability sign-off
- Unavailable/degraded behavior is confirmed at the agent/runtime layer and by cached display data continuing to serve during backend outage, but the exact on-screen fallback wording still needs a human visual pass

### Still requires manual on-device confirmation

- Specific `no keg` screen, because the live pilot tap assignment was not deliberately removed during this bring-up
- `authorized`
- `denied`
- `pouring`
- `finished`

These interactive states require a person at the device with the real tap/card path.

## 7. Fixes Made

- repaired `cybeer-hub` deployment with timestamped backup, clean checkout replacement, restored `.env`, added `DISPLAY_API_KEY`, and rebuilt compose services
- fixed Raspberry Pi backend reachability through `/etc/beer-tap/device.env` with Pi-local IP override
- confirmed and used the live controller/display runtime chain:
  - controller -> runtime file
  - display agent -> local bootstrap/runtime endpoints
  - Chromium -> local display URL
- kept portrait at the output/compositor layer with `wlr-randr`
- switched the pilot kiosk startup path to explicit `labwc` autostart for reliable relaunch after graphical-session restarts
- taught `scripts/encoding_guard.py --all` to ignore synced `.venv-*` runtime environments so the repository-wide check reflects source files instead of device-local virtualenv vendor trees
- updated deployment artifacts:
  - `deploy/rpi/tap-display-kiosk.sh`
  - `deploy/rpi/labwc-autostart`
  - `deploy/rpi/README.md`
  - `.gitignore`

## 8. Remaining Non-blocking Limitations

- Pi pilot still relies on IP override instead of hostname resolution for `cybeer-hub`
- kiosk supervision is still session-based rather than a dedicated watchdog/service wrapper
- final visual confirmation of some on-screen states still needs a person at the monitor
- full interactive pour-state validation still depends on real card/tap hardware interaction

## 9. Final Verdict

`DISPLAY BRING-UP READY ON PI`

Why:

- the Raspberry Pi now reaches the backend reliably for the pilot path
- controller and display agent are active and healthy on-device
- Chromium kiosk autostarts on the Pi and survives `lightdm` restarts
- portrait orientation is applied at the right layer for the real monitor
- backend content reaches the screen path
- degraded backend behavior keeps cached display data available instead of collapsing into an empty local display path

The remaining gaps are manual validation items for specific live interaction states, not bring-up blockers for pilot hardware readiness.
