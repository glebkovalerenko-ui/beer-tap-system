# Raspberry Pi Tap Display Deployment

Artifacts in this directory are MVP deployment examples for one controller/display pair on a Raspberry Pi.

Expected paths on device:

- repo checkout: `/opt/beer-tap-system`
- shared device env: `/etc/beer-tap/device.env`
- controller runtime JSON: `/run/beer-tap/display-runtime.json`
- controller venv: `/opt/beer-tap-system/.venv-controller`
- display-agent venv: `/opt/beer-tap-system/.venv-display-agent`

Install flow:

1. Build the display client bundle on the device checkout:
   - `cd /opt/beer-tap-system/tap-display-client`
   - `npm ci`
   - `npm run build`
2. Copy `device.env.example` to `/etc/beer-tap/device.env` and set:
   - `TAP_ID`
   - `SERVER_URL`
   - `INTERNAL_TOKEN` for controller/internal traffic
   - `DISPLAY_API_KEY` for tap-display-agent read-only snapshot/media access
3. Create Python environments:
   - `python3 -m venv /opt/beer-tap-system/.venv-controller`
   - `/opt/beer-tap-system/.venv-controller/bin/pip install -r /opt/beer-tap-system/rpi-controller/requirements.txt`
   - `python3 -m venv /opt/beer-tap-system/.venv-display-agent`
   - `/opt/beer-tap-system/.venv-display-agent/bin/pip install -r /opt/beer-tap-system/tap-display-agent/requirements.txt`
   - `/opt/beer-tap-system/.venv-display-agent/bin/pip install uvicorn`
4. Copy systemd units from this folder into `/etc/systemd/system/`:
   - `beer-tap-controller.service`
   - `tap-display-agent.service`
5. Reload and enable services:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now beer-tap-controller.service tap-display-agent.service`
6. Configure autologin and add `tap-display-kiosk.desktop` into the kiosk session autostart.

Chromium target URL:

- `http://127.0.0.1:18181/display/`

Minimum pilot bring-up checks on the Pi:

1. Verify the local agent is alive:
   - `curl -fsS http://127.0.0.1:18181/health`
2. Verify cached content/runtime endpoints respond:
   - `curl -fsS http://127.0.0.1:18181/local/display/bootstrap`
   - `curl -fsS http://127.0.0.1:18181/local/display/runtime`
3. Verify controller runtime file updates:
   - `sudo cat /run/beer-tap/display-runtime.json`
4. Check service health if startup looks wrong:
   - `sudo systemctl status beer-tap-controller.service tap-display-agent.service`
   - `sudo journalctl -u beer-tap-controller.service -u tap-display-agent.service --since "10 min ago"`
5. Kiosk smoke:
   - log in through the kiosk/autologin session
   - confirm Chromium opens `http://127.0.0.1:18181/display/`
   - close Chromium once and confirm the launcher reopens it
   - restart `tap-display-agent.service` and confirm the page recovers without manual backend/file edits

Hardening notes in this MVP package:

- `tap-display-agent` now requires `DISPLAY_API_KEY` and uses `X-Display-Token` instead of the broad internal-token path.
- The kiosk launcher waits for the local agent health endpoint before opening Chromium.
- Chromium is relaunched by the launcher script if it exits.
- This is still pilot-grade deployment: there is no fleet management, remote watchdog, or screenshot telemetry in this package.
