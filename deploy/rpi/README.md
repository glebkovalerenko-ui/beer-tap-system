# Raspberry Pi Tap Display Deployment

Artifacts in this directory are MVP deployment examples for one controller/display pair on a Raspberry Pi.

Expected pilot layout on device:

- repo checkout: `/home/cybeer/beer-tap-system`
- shared device env: `/etc/beer-tap/device.env`
- controller runtime JSON: `/run/beer-tap/display-runtime.json`
- runtime root: `/home/cybeer/.local/share/beer-tap`
- runtime venv root: `/home/cybeer/.local/share/beer-tap/venvs`
- controller venv: `/home/cybeer/.local/share/beer-tap/venvs/controller`
- display-agent venv: `/home/cybeer/.local/share/beer-tap/venvs/display-agent`
- kiosk user: `cybeer`

Pilot network default:

- `SERVER_URL=http://192.168.0.110:8000`
- Keep hostname-based defaults elsewhere in the repo; this file is the Pi-local override for the current pilot because `cybeer-hub` is not resolvable on the Pi and `/etc/hosts` is cloud-init managed.

Install required OS packages on the Pi before enabling services:

- controller deps: `python3-venv python3-pip pcscd libccid python3-pyscard python3-gpiozero python3-lgpio`
- kiosk deps: `chromium lightdm labwc wlr-randr`

Install flow:

1. Build the display client bundle on the device checkout:
   - `cd /home/cybeer/beer-tap-system/tap-display-client`
   - `npm ci`
   - `npm run build`
2. Copy `device.env.example` to `/etc/beer-tap/device.env` and set:
   - `TAP_ID`
   - `SERVER_URL` (`http://192.168.0.110:8000` for the current pilot)
   - `INTERNAL_TOKEN` for controller/internal traffic; it must match hub `INTERNAL_API_KEY` (or one of `INTERNAL_API_KEYS`)
   - `DISPLAY_API_KEY` for tap-display-agent read-only snapshot/media access; it must match backend `DISPLAY_API_KEY` (or one of `DISPLAY_API_KEYS`)
   - do not leave placeholder or demo token values in pilot
3. Provision runtime environments outside the synced repo path:
   - `chmod 755 /home/cybeer/beer-tap-system/deploy/rpi/provision-runtime-venvs.sh`
   - `sudo /home/cybeer/beer-tap-system/deploy/rpi/provision-runtime-venvs.sh`
   - the script is idempotent and safe to rerun after dependency changes
   - the script enforces:
     - runtime root `/home/cybeer/.local/share/beer-tap`
     - runtime venv root `/home/cybeer/.local/share/beer-tap/venvs`
     - owner/group `cybeer:cybeer`
     - root directory mode `0755`
   - controller venv uses `python3 -m venv --system-site-packages` so distro-installed `python3-pyscard`, `python3-gpiozero`, and `python3-lgpio` remain available from the external env
   - display-agent venv uses a standard `python3 -m venv`
4. Copy systemd units from this folder into `/etc/systemd/system/`:
   - `beer-tap-controller.service`
   - `tap-display-agent.service`
5. Reload and enable services:
   - `sudo systemctl daemon-reload`
    - `sudo systemctl enable --now beer-tap-controller.service tap-display-agent.service`
6. Enable graphical autologin for `cybeer` with `labwc` and install the session autostart hook:
   - `mkdir -p /home/cybeer/.config/labwc`
   - copy `deploy/rpi/labwc-autostart` to `/home/cybeer/.config/labwc/autostart`
   - `chmod 755 /home/cybeer/.config/labwc/autostart`
   - `tap-display-kiosk.desktop` can stay as an optional fallback for desktop environments that honor XDG autostart, but the pilot Pi should use `labwc` autostart because it survived repeated `lightdm` restarts on-device
7. Portrait is handled at the compositor/output layer, not in Chromium or CSS:
   - install `wlr-randr`
   - the kiosk launcher applies `HDMI-A-1 -> transform 90` before opening Chromium
   - override `KIOSK_OUTPUT_NAME` or `KIOSK_OUTPUT_TRANSFORM` only if the monitor enumerates differently

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
   - log in through the kiosk/autologin session as `cybeer`
   - confirm the monitor is portrait rather than landscape
   - confirm Chromium opens `http://127.0.0.1:18181/display/`
   - close Chromium once and confirm the launcher reopens it
   - restart `tap-display-agent.service` and confirm the page recovers without manual backend/file edits

Hardening notes in this MVP package:

- `tap-display-agent` now requires `DISPLAY_API_KEY` and uses `X-Display-Token` instead of the broad internal-token path.
- `rpi-controller` now requires explicit `INTERNAL_TOKEN`/`INTERNAL_API_KEY` config and no longer falls back to `demo-secret-key`.
- The kiosk launcher waits for the local agent health endpoint before opening Chromium.
- The kiosk launcher prefers `chromium`, falls back to `chromium-browser`, and forces a predictable Wayland session env (`XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, `XDG_SESSION_TYPE`) for the pilot Pi.
- The kiosk launcher reapplies portrait rotation through `wlr-randr` before opening Chromium.
- The kiosk launcher writes a startup banner and relaunch events into `~/.local/state/tap-display-kiosk.log` so reboot failures can be diagnosed from one file.
- Chromium is launched with `--disable-gpu` on the pilot Pi because the live device showed Wayland/EGL context failures after reboot and the display UI does not need GPU acceleration.
- Chromium is relaunched by the launcher script if it exits.
- The pilot Pi uses `labwc` session autostart rather than relying on `~/.config/autostart/*.desktop`, because the explicit `labwc` hook was the reliable path during real-device bring-up.
- Pi systemd services must not depend on virtual environments inside the Syncthing-managed repo path. The live service contract is the external runtime root under `/home/cybeer/.local/share/beer-tap/venvs`.
- See `SECURITY_BASELINE.md` in the repo root for the controlled-pilot auth/secrets contract.
- This is still pilot-grade deployment: there is no fleet management, remote watchdog, or screenshot telemetry in this package.
