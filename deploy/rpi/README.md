# Raspberry Pi Tap Display Deployment

Artifacts in this directory are MVP deployment examples for one controller/display pair on a Raspberry Pi.

Expected paths on device:

- repo checkout: `/opt/beer-tap-system`
- shared device env: `/etc/beer-tap/device.env`
- controller runtime JSON: `/run/beer-tap/display-runtime.json`
- controller venv: `/opt/beer-tap-system/.venv-controller`
- display-agent venv: `/opt/beer-tap-system/.venv-display-agent`

Install flow:

1. Copy `device.env.example` to `/etc/beer-tap/device.env` and set:
   - `TAP_ID`
   - `SERVER_URL`
   - `INTERNAL_TOKEN` for controller/internal traffic
   - `DISPLAY_API_KEY` for tap-display-agent read-only snapshot/media access
2. Install Python environments for `rpi-controller` and `tap-display-agent`.
3. Copy systemd units from this folder into `/etc/systemd/system/`.
4. Enable and start:
   - `beer-tap-controller.service`
   - `tap-display-agent.service`
5. Configure autologin and add `tap-display-kiosk.desktop` into the kiosk session autostart.

Chromium target URL:

- `http://127.0.0.1:18181/display/`

Hardening notes in this MVP package:

- `tap-display-agent` now requires `DISPLAY_API_KEY` and uses `X-Display-Token` instead of the broad internal-token path.
- The kiosk launcher waits for the local agent health endpoint before opening Chromium.
- Chromium is relaunched by the launcher script if it exits.
- This is still pilot-grade deployment: there is no fleet management, remote watchdog, or screenshot telemetry in this package.
