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

### Follow-up: real display stuck in `processing_sync` after zero-volume card session

During the physical smoke, the user reported that the display stayed on `Кран завершает синхронизацию` after the card had already been removed.

Live evidence collected immediately after that report:

- Pi runtime endpoint was already back to idle:
  - `/local/display/runtime` returned `phase="idle"` and `card_present=false`
- Pi bootstrap endpoint was still serving a backend snapshot with:
  - `snapshot.tap.status="processing_sync"`
- Hub snapshot API returned the same live backend state:
  - `tap.status="processing_sync"`
- Live DB inspection on the hub showed one stuck placeholder and one active lock for tap `1`:
  - `pending_count=1`
  - `active_visit_count=1`
  - pending row card UID: `0b24b1cd`

Additional root cause:

- `authorize_pour_lock()` intentionally creates a `pending_sync` placeholder and sets `tap.status="processing_sync"` as soon as authorization is granted.
- The controller only wrote a local sync record when `total_volume_ml > 1`.
- In the reproduced real session, the card was authorized but no measurable pour volume was recorded, so the controller never emitted any terminal sync row.
- Because no `/api/sync/pours` terminal event ever arrived, the backend placeholder remained `pending_sync`, the visit lock remained set, and the display snapshot legitimately stayed in `processing_sync`.

Additional fix:

- Updated `rpi-controller/flow_manager.py` so an authorized session that ends with `0 ml` now still writes a terminal local sync row.
- Updated `backend/crud/pour_crud.py` so a sync payload with `volume_ml <= 0` finalizes the pending placeholder as terminal `rejected`, clears `active_tap_id`, and restores `tap.status="active"`.
- Added regression tests for both sides:
  - controller zero-volume terminal sync creation
  - backend zero-volume sync rejection plus unlock
- For the already stuck live placeholder, sent a one-shot internal zero-volume sync after deploying the code fix.

Follow-up verification after rollout:

- Hub sync endpoint returned:
  - `status="rejected"`
  - `outcome="rejected_zero_volume"`
  - `reason="zero_volume_session"`
- Live DB then showed:
  - `tap_status active`
  - `pending_count 0`
  - `rejected_status rejected`
  - `rejected_volume 0`
  - `active_visit_count 0`
- Hub display snapshot for tap `1` returned:
  - `tap.status="active"`
- Pi display bootstrap and runtime then aligned again:
  - bootstrap snapshot `tap.status="active"`
  - runtime `phase="idle"`

This corrected the inaccurate intermediate conclusion that the system had simply returned to idle. The runtime had returned to idle, but the backend display snapshot had remained stuck in `processing_sync` until this zero-volume terminal sync path was fixed.

### Follow-up: active card session was still visually overridden by `processing_sync`

After the zero-volume terminal sync fix above, the user still reported unstable display behavior during real card holds without opening the tap:

- `Откройте кран`
- then after roughly `5` to `10` seconds: `Кран завершает синхронизацию`
- then later `Налив завершен` or `Налив остановлен`
- then a short post-remove service screen before returning to idle

Live controller evidence showed the session itself was stable:

- controller journal on `2026-03-17 15:26:13 MSK` and `2026-03-17 15:26:41 MSK` recorded one continuous authorized session with repeated `Налив: 0 мл ...`
- no early `card_removed` termination happened during those holds
- the session only ended at `FLOW_TIMEOUT_SECONDS`, then queued and synced a zero-volume terminal record immediately

Additional root cause:

- backend `authorize_pour_lock()` creates the placeholder pending pour at authorize time and immediately sets `tap.status="processing_sync"`
- display bootstrap polling can therefore observe `processing_sync` while the same tap is still in a live authorized session
- that service-state snapshot is operationally correct for backend sync bookkeeping, but it is not the right user-facing state while the active visit lock is still held on that tap
- in parallel, NFC presence sampling was too sensitive to short reader-presence dips, which made some earlier card-removal timing feel erratic

Additional fix:

- `tap-display-client/src/display-state.js`
  - active runtime states now take precedence over snapshot service states such as `processing_sync`
- `backend/crud/display_crud.py`
  - display snapshots now mask `tap.status="processing_sync"` to `active` when there is still an active visit with `active_tap_id` on that tap
  - this keeps backend locking semantics intact while preventing the display snapshot from advertising a sync-only service state during a live session
- `rpi-controller/flow_manager.py`
  - added `AUTHORIZED_CARD_ABSENCE_DEBOUNCE_SECONDS = 0.8`
  - an authorized session now requires sustained absence before treating the card as removed
  - zero-volume authorized sessions also trigger an immediate sync cycle after the local terminal row is written

Additional verification:

- frontend state tests passed:
  - `node --test tap-display-client/test/display-state.test.js`
- controller runtime tests passed:
  - `python -m pytest rpi-controller/test_flow_manager.py`
- backend display snapshot and offline-sync tests passed:
  - `DATABASE_URL=sqlite:///./backend-test.db python -m pytest backend/tests/test_tap_display_api.py backend/tests/test_m4_offline_sync_reconcile.py`
- encoding guard passed:
  - `python scripts/encoding_guard.py --all`
- hub rollout:
  - updated `backend/crud/display_crud.py`
  - restarted only `beer_backend_api` in Docker Compose
  - container returned `healthy`
- final physical monitor verification on `2026-03-17`:
  - during card hold without opening the tap, the user saw `Откройте кран`
  - the display no longer switched to `Кран завершает синхронизацию` mid-session
  - at timeout the user saw `Налив остановлен`
  - after card removal, `Налив остановлен` stayed only briefly and then the display returned to the beer/tap idle screen

## 5. Post-restoration Stage 2 — display responsiveness and controller stability

### Scope

After the runtime restore above, the system was operational but still felt unstable in live use:

- the display reacted later than the valve on card-present
- `processing_sync` could stay visible for a variable amount of time after short pours
- repeated fast card taps could end on confusing service-state screens
- some sessions still showed `Нет связи с системой`
- one intermediate local edit corrupted `tap-display-client/src/App.svelte` and produced mojibake on multiple screens

The goal of this follow-up was not a redesign. It was a bounded stabilization pass on the existing Pi runtime path.

### Evidence

Display/UI timing evidence gathered on `2026-03-17` and `2026-03-18`:

- idle runtime polling in the browser was still gated by the display polling contract rather than a push channel
- the user consistently reported that the valve reacted before the `Откройте кран` screen appeared
- long `processing_sync` durations correlated with the sync worker interval rather than with a permanently stuck state
- repeated quick card touches could still surface generic service-state UX

Controller/network evidence gathered on `2026-03-18`:

- controller log at `2026-03-18 07:45:09 MSK` recorded:
  - `authorize_request_failed: http://192.168.0.110:8000/api/visits/authorize-pour: ... Read timed out. (read timeout=5)`
- the same controller then mapped that request failure into:
  - `reason_code=backend_unreachable`
- display-agent health stayed good during these episodes:
  - `backend_link_lost=false`
  - `controller_runtime_stale=false`
- direct Pi-to-hub reachability was healthy at the same time:
  - manual request to `authorize-pour` later returned a normal business response in about `0.111s`

Platform evidence gathered on the Pi around the same failures:

- `Undervoltage detected!`
- `vcgencmd get_throttled` reported `0xd0000`
- kernel logged multiple `dwc_otg_hcd_urb_dequeue ... Timed out`
- `pcscd` logged repeated card power-up / removed-card errors

This showed that the remaining `Нет связи` episodes were not caused by the display client. They were transient controller authorize failures, very likely amplified by Pi power/USB instability.

### Additional fixes

Display/UI follow-up:

- `tap-display-client/src/App.svelte`
  - idle polling reduced from `1000 ms` to `250 ms`
  - runtime/bootstrap state moved onto explicit Svelte stores
  - UI state resolution now depends on explicit reactive inputs instead of hidden dependencies
  - `authorizing` gained a short UI grace period so a very fast authorize does not flash `Подождите`
  - explicit `card_removed` copy added:
    - `Заберите карту`
    - `Уберите карту со считывателя`
- `tap-display-client/src/display-state.js`
  - `card_removed` preserved as an explicit blocked service code instead of collapsing into generic maintenance

Controller/runtime follow-up:

- `rpi-controller/sync_manager.py`
  - `flow-events` moved off the hot loop into a dedicated background queue/worker
  - sync worker gained explicit wake-up via `notify_sync_needed()`
  - pour sync is no longer forced to wait only for the fixed interval
  - authorize path now retries once after a transient `RequestException`, recreating the authorize session before retry
- `rpi-controller/main.py`
  - starts the flow-event worker
  - sync worker now waits on `wait_for_next_sync_cycle()` instead of unconditional sleep
- `rpi-controller/flow_manager.py`
  - wakes the sync worker immediately after a local pour is written
  - zero-volume card-removed sessions return runtime to `idle` immediately after completion instead of visually hanging on the active screen
- `rpi-controller/hardware.py`
  - PC/SC reader enumeration / connection setup is now wrapped so transient `pyscard` failures do not crash the whole controller process

UTF-8 / mojibake follow-up:

- a local encoding regression in `tap-display-client/src/App.svelte` briefly produced mojibake on the kiosk
- the file was restored to clean UTF-8, rebuilt, redeployed, and protected again by `encoding_guard`

### Verification

Relevant repo checks on the assembled release line:

- `python -m pytest rpi-controller/test_sync_manager.py rpi-controller/test_flow_manager.py rpi-controller/test_hardware_resilience.py`
- `node --test tap-display-client/test/display-state.test.js`
- `npm run build` in `tap-display-client`
- `python scripts/encoding_guard.py --all`

Live rollout and verification on the Pi:

- controller restarted successfully from the external runtime path:
  - `/home/cybeer/.local/share/beer-tap/venvs/controller/bin/python`
- local display runtime stayed healthy:
  - `phase="idle"`
  - `controller_runtime_stale=false`
- rebuilt kiosk bundle was served from:
  - `/display/assets/index-Cr7mfanH.js`
- physical text rendering recovered from mojibake and remained stable

Final practical user verification:

- `Нет связи` could no longer be reproduced in repeated normal taps after the authorize retry fix
- the overall start now felt better to the user and explicitly “not worse”
- after more than five very short tap-only interactions without pouring, the display showed `Заберите карту`
  - this is now the intended explicit `card_removed` path, not a generic maintenance/service fallback

### Result

The software side of Stage 2 was completed:

- display transitions are faster and more predictable
- `processing_sync` behavior is no longer governed by a blind fixed wait after every short session
- repeated fast card interactions surface an explicit user-facing state instead of a misleading generic one
- a single transient authorize timeout no longer immediately degrades into the same user-visible failure mode

The main residual risk is now below the application layer:

- Pi power / USB instability can still produce transient stalls
- this remains visible in `Undervoltage`, `dwc_otg`, and `pcscd` logs

## 6. Remaining limitations

- The kiosk launcher still logs some Chromium GPU-process noise on this Pi platform, but Chromium relaunches and the UI remains visible after boot. This is not the current blocker.
- `local_journal.db` remains part of controller runtime operation under the repo path. That behavior was pre-existing and was not changed in this hotfix.
- The strongest remaining operational risk is hardware-side:
  - Pi power sag / USB instability can still affect NFC and controller responsiveness even though the software path now degrades more gracefully.

## 7. Final verdict

`PI RUNTIME RESTORED`
