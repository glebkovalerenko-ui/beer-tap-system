# Pi Runtime Regression: Black Screen And ACR122U RCA

## 1. Problem statement

- Raspberry Pi kiosk booted into a black screen with a mouse cursor instead of the Tap Display UI.
- ACR122U NFC reader appeared non-working on the Raspberry Pi.

## 2. Environment

- Date of investigation and fix: `2026-03-17`
- Pi host: `cybeer-00`
- Pi repo path: `/home/cybeer/beer-tap-system`
- Base branch for hotfix work: `investigation/processing-sync-stuck`
- Hotfix branch: `hotfix/pi-runtime-black-screen-and-acr122u`
- Device env path: `/etc/beer-tap/device.env`
- Display runtime path: `/run/beer-tap/display-runtime.json`
- Live display session:
  - `lightdm` active
  - `lightdm-autologin` session for `cybeer`
  - `Desktop=labwc`
  - `Type=wayland`

Pre-fix installed unit `ExecStart` values:

- controller old path:
  - `/home/cybeer/beer-tap-system/.venv-controller/bin/python main.py`
- display-agent old path:
  - `/home/cybeer/beer-tap-system/.venv-display-agent/bin/uvicorn main:app --host 127.0.0.1 --port 18181`

Post-fix installed unit `ExecStart` values:

- controller new path:
  - `/home/cybeer/.local/share/beer-tap/venvs/controller/bin/python main.py`
- display-agent new path:
  - `/home/cybeer/.local/share/beer-tap/venvs/display-agent/bin/uvicorn main:app --host 127.0.0.1 --port 18181`

## 3. RCA A — kiosk/display regression

### Evidence before fix

- `systemctl status lightdm` showed `active (running)` on `2026-03-17 11:17 MSK`.
- `loginctl show-session 2` showed an active `lightdm-autologin` session with `Desktop=labwc` and `Type=wayland`.
- Process inventory showed:
  - `labwc` running
  - `/bin/sh /home/cybeer/beer-tap-system/deploy/rpi/tap-display-kiosk.sh` running
  - no Chromium process
- `~/.local/state/tap-display-kiosk.log` showed the launcher repeatedly stopping at:
  - `waiting for display agent health_url=http://127.0.0.1:18181/health`
- Local display-agent endpoints were down:
  - `http://127.0.0.1:18181/health`
  - `/local/display/bootstrap`
  - `/local/display/runtime`
- `tap-display-agent.service` was in `203/EXEC` restart loop:
  - `Unable to locate executable '/home/cybeer/beer-tap-system/.venv-display-agent/bin/uvicorn'`
- The repo-local display-agent executable path was actually missing:
  - `/home/cybeer/beer-tap-system/.venv-display-agent/bin/uvicorn: No such file or directory`

### Root cause

- The graphical session and kiosk launcher were not the failing layer.
- The kiosk launcher correctly waited for the local display-agent.
- The actual breakage was that `tap-display-agent.service` still pointed to a deleted repo-local virtualenv path.
- Because the local agent never started, `tap-display-kiosk.sh` never reached Chromium launch and the monitor remained on a black session background with cursor.

### Fix

- Moved the display-agent service runtime to an external, non-Syncthing-managed path:
  - `/home/cybeer/.local/share/beer-tap/venvs/display-agent`
- Added idempotent provisioning script:
  - `deploy/rpi/provision-runtime-venvs.sh`
- Updated installed unit to:
  - `ExecStart=/home/cybeer/.local/share/beer-tap/venvs/display-agent/bin/uvicorn main:app --host 127.0.0.1 --port 18181`
- Enforced runtime root ownership and mode:
  - `/home/cybeer/.local/share/beer-tap` -> `cybeer:cybeer`, `0755`
  - `/home/cybeer/.local/share/beer-tap/venvs` -> `cybeer:cybeer`, `0755`

### Verification

After `daemon-reload` and service restart:

- `systemctl cat tap-display-agent.service` showed the new external `ExecStart`.
- `systemctl show -p ExecStart tap-display-agent.service` resolved to:
  - `path=/home/cybeer/.local/share/beer-tap/venvs/display-agent/bin/uvicorn`
- `tap-display-agent.service` became `active (running)`.
- `curl -fsS http://127.0.0.1:18181/health` returned HTTP `200`.
- `curl -fsS http://127.0.0.1:18181/local/display/bootstrap` returned cached tap snapshot data.
- `curl -fsS http://127.0.0.1:18181/local/display/runtime` returned live runtime payload.
- `tap-display-kiosk.log` advanced from `waiting for display agent` to:
  - `display agent is reachable`
  - `launching chromium in kiosk mode`
- Chromium process tree appeared with `--app=http://127.0.0.1:18181/display/`.

After full reboot on `2026-03-17 11:22:41 MSK`:

- `lightdm` came back `active`.
- `labwc`, `tap-display-kiosk.sh`, and Chromium all came back automatically.
- `systemctl cat tap-display-agent.service` still showed the external path.
- `systemctl show -p ExecStart tap-display-agent.service` still resolved to the external path, not repo-local `.venv-display-agent`.
- Physical monitor check: Tap Display UI was visible and showed tap and beer information instead of a black screen with cursor.

## 4. RCA B — ACR122U regression

### USB evidence

- `lsusb` pre-fix and post-fix both showed:
  - `072f:2200 Advanced Card Systems, Ltd ACR122U`
- Boot journal showed normal attach events:
  - `Product: ACR122U PICC Interface`
  - `Manufacturer: ACS`
- No evidence indicated a dead USB port or total reader invisibility.

### PC/SC evidence

- `pcscd.socket` was active.
- `python3` with `smartcard.System.readers()` returned:
  - `['ACS ACR122U PICC Interface 00 00']`
- Post-fix controller external env also saw the same reader:
  - `['ACS ACR122U PICC Interface 00 00']`

### Controller evidence before fix

- `beer-tap-controller.service` was in `203/EXEC` restart loop:
  - `Unable to locate executable '/home/cybeer/beer-tap-system/.venv-controller/bin/python'`
- The repo-local controller executable path was actually missing:
  - `/home/cybeer/beer-tap-system/.venv-controller/bin/python: No such file or directory`
- Because the controller process was down, the application never polled the NFC reader and never published runtime updates.

### Root cause

- The NFC reader itself was not broken on Raspberry Pi.
- USB detection and PC/SC reader enumeration were both healthy.
- The actual failure was higher in the stack: the controller service still pointed to a deleted repo-local virtualenv path and therefore never started.

### Fix

- Moved controller runtime to an external, non-Syncthing-managed path:
  - `/home/cybeer/.local/share/beer-tap/venvs/controller`
- Updated installed unit to:
  - `ExecStart=/home/cybeer/.local/share/beer-tap/venvs/controller/bin/python main.py`
- Provisioned controller venv with:
  - `python3 -m venv --system-site-packages`
- This preserved access to distro-installed hardware/PCSC packages while keeping service binaries outside the synced repo path.

### Controller external-env import proof

Recorded from the new external controller env:

- `sys.executable=/home/cybeer/.local/share/beer-tap/venvs/controller/bin/python`
- `smartcard=/usr/lib/python3/dist-packages/smartcard/__init__.py`
- `gpiozero=/usr/lib/python3/dist-packages/gpiozero/__init__.py`
- `lgpio=/usr/lib/python3/dist-packages/lgpio.py`

This confirmed that the controller service now runs through the external Python path and that `pyscard`, `gpiozero`, and `lgpio` are importable there.

### Verification

After `daemon-reload` and service restart:

- `systemctl cat beer-tap-controller.service` showed the new external `ExecStart`.
- `systemctl show -p ExecStart beer-tap-controller.service` resolved to:
  - `path=/home/cybeer/.local/share/beer-tap/venvs/controller/bin/python`
- `beer-tap-controller.service` became `active (running)`.
- Controller startup log showed successful backend probe:
  - `Проверка сервера при запуске успешна ... код_ответа=200`
- `/run/beer-tap/display-runtime.json` was recreated and updated continuously.

After full reboot:

- `systemctl cat beer-tap-controller.service` still showed the external path.
- `systemctl show -p ExecStart beer-tap-controller.service` still resolved to the external path, not repo-local `.venv-controller`.
- The reader remained visible through `smartcard.System.readers()`.

Practical card-read smoke on `2026-03-17 13:25:47 MSK`:

- Physical check:
  - card was presented to ACR122U
  - display visibly transitioned into an “open tap” style state
- Controller journal captured real reader-driven runtime behavior:
  - `Авторизация подтверждена для карты 0b24b1cd на кране 1. Открываем клапан, лимит 98 мл.`
  - repeated live session progress lines followed
  - `Клапан закрыт: причина=card_removed`
  - `Сессия завершена. Налито: 0 мл`
- After card removal, runtime safely returned to:
  - `phase="idle"`
  - `card_present=false`

This proved the restored controller process could see the real reader, read the real card, authorize a session, update runtime/UI state, and handle card removal correctly on the Pi.

## 5. Remaining limitations

- The kiosk launcher still logs some Chromium GPU-process noise on this Pi platform, but Chromium relaunches and the UI remains visible after boot. This is not the current blocker.
- `local_journal.db` remains part of controller runtime operation under the repo path. That behavior was pre-existing and was not changed in this hotfix.

## 6. Final verdict

`PI RUNTIME RESTORED`
