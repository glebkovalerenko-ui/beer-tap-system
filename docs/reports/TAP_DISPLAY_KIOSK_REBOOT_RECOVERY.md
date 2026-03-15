# Tap Display Kiosk Reboot Recovery

## 1. Problem statement

On March 15, 2026, after `sudo reboot` on Raspberry Pi controller `cybeer@192.168.0.114`, the expected Tap Display kiosk UI did not come back through a clean, documented startup path.

Observed user-facing symptom:

- the physical panel was reported as a gray screen with a mouse cursor instead of the Tap Display UI

The goal of this hotfix was to restore a reproducible post-reboot kiosk path without changing backend/product behavior.

## 2. Audit findings

Facts gathered from the live Pi before the fix:

- Windows repo base was `feature/tap-display-real-pi-bringup` at `8f40724`.
- Pi checkout was still on `3256c6c` on the same branch name, not on the current branch head.
- Pi worktree was dirty and mixed manual bring-up changes with older git state:
  - modified: `.gitignore`, `deploy/rpi/README.md`, `deploy/rpi/tap-display-kiosk.sh`, `scripts/encoding_guard.py`
  - untracked: `deploy/rpi/labwc-autostart`, `docs/reports/TAP_DISPLAY_REAL_PI_BRINGUP_AND_PORTRAIT_SMOKE.md`
- Active runtime before normalization already showed that backend/content was not the blocker:
  - `beer-tap-controller.service` was active
  - `tap-display-agent.service` was active
  - `lightdm` was active
  - `labwc` session existed
  - `http://127.0.0.1:18181/health` returned `200`
  - `http://127.0.0.1:18181/local/display/bootstrap` returned a valid snapshot
  - `http://127.0.0.1:18181/local/display/runtime` returned a valid runtime payload
- The reliable kiosk autostart path already existed only as manual device state:
  - `~/.config/labwc/autostart` was present
  - `~/.config/autostart/tap-display-kiosk.desktop` also existed as fallback
- Chromium stderr in `~/.local/state/tap-display-kiosk.log` showed repeated Wayland/GPU failures before the fix:
  - `eglCreateContext: Requested version is not supported`
  - `GPU process launch failed: error_code=1002`
  - `GPU process isn't usable. Goodbye.`

Facts gathered after the fix and reboot:

- Pi was backed up to `/home/cybeer/kiosk-reboot-recovery-20260315-200722` before normalization.
- Pi was moved onto clean branch `hotfix/tap-display-kiosk-reboot` at `05b52d2`.
- After reboot at `2026-03-15T20:08:57+03:00`:
  - `lightdm`, `beer-tap-controller.service`, and `tap-display-agent.service` came back active
  - `lightdm` autologin returned to a live `labwc` session (`session-2.scope`)
  - `~/.config/labwc/autostart` invoked `deploy/rpi/tap-display-kiosk.sh`
  - launcher log markers appeared again at `2026-03-15T17:09:28Z`
  - Chromium kiosk process relaunched inside the same session
  - `/health`, `/local/display/bootstrap`, and `/local/display/runtime` still returned `200`
- Forced browser-exit recovery was verified:
  - old kiosk Chromium PID `1330` was terminated
  - launcher logged `chromium exited exit_code=0; restarting in 2 seconds`
  - a new kiosk Chromium PID `3123` appeared

## 3. Root cause

The primary root cause was deployment drift in the kiosk startup path.

The Pi was not running a clean, canonical bring-up state after reboot. Instead, it was on stale commit `3256c6c` while the reliable `labwc` autostart fix from the newer branch state existed only as manual, uncommitted device changes. That meant the post-reboot kiosk path was not reproducible from git and could not be trusted as the authoritative startup path.

Secondary contributing risk:

- the live Chromium Wayland/GPU path on this Pi showed repeated EGL/GPU-process failures
- that made the kiosk more fragile after reboot even when the session itself was alive

In short:

- backend/content path was healthy
- session/bootstrap path was drifting outside git
- Chromium GPU startup on the Pi was noisy and not reliable enough for pilot reboot behavior

## 4. Fix implemented

Implemented changes:

- created `hotfix/tap-display-kiosk-reboot` from local `feature/tap-display-real-pi-bringup` head
- pushed the hotfix branch before touching the Pi checkout
- backed up the dirty Pi worktree and pre-fix audit artifacts outside the repo
- normalized the Pi onto clean branch `hotfix/tap-display-kiosk-reboot`
- reinstalled the authoritative `labwc` autostart hook from git:
  - repo source: `deploy/rpi/labwc-autostart`
  - live install target: `~/.config/labwc/autostart`
- kept `tap-display-kiosk.desktop` only as non-primary fallback
- hardened `deploy/rpi/tap-display-kiosk.sh`:
  - explicit `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, `XDG_SESSION_TYPE`
  - startup banner and relaunch logging into `~/.local/state/tap-display-kiosk.log`
  - deterministic Chromium flag set
  - `--disable-gpu` added for Pi pilot stability
  - relaunch loop preserved
- updated `deploy/rpi/README.md` to document the hardened launcher behavior

## 5. Post-fix verification

Verified by SSH/runtime checks:

- `beer-tap-controller.service` active after reboot
- `tap-display-agent.service` active after reboot
- `lightdm` active after reboot
- `labwc` autologin session active after reboot
- launcher process active after reboot:
  - `/bin/sh /home/cybeer/beer-tap-system/deploy/rpi/tap-display-kiosk.sh`
- Chromium kiosk process active after reboot with the expected local app URL:
  - `--app=http://127.0.0.1:18181/display/`
  - `--disable-gpu`
- local endpoints healthy after reboot:
  - `/health`
  - `/local/display/bootstrap`
  - `/local/display/runtime`
- launcher restart loop confirmed by killing kiosk Chromium once and observing a new Chromium PID plus relaunch log entries

Not directly verified from SSH alone:

- final physical panel image on the monitor still requires a human glance to conclusively say "Tap Display UI is visible" versus "browser window exists but the panel output is still wrong"

## 6. Remaining limitations

- The final physical screen result was not directly observable from this SSH-only session.
- Headless Chromium rendering is not a trustworthy proxy for the real kiosk panel here; it still reported `booting` despite live local endpoints returning valid snapshot/runtime payloads.
- Chromium still spawns a helper process labeled as `gpu-process`, but with `--disable-gpu` the kiosk no longer hit the earlier fatal GPU startup exit path during the verified reboot/relaunch pass.
- This remains pilot-grade kiosk supervision through graphical session autostart, not a dedicated watchdog service.

## 7. Final verdict

`MOSTLY FIXED, SMALL FOLLOW-UP NEEDED`

Why:

- the reboot-time startup chain is now clean, git-backed, and reproducible
- the Pi returns to `lightdm -> labwc -> labwc autostart -> tap-display-kiosk.sh -> Chromium`
- Chromium is relaunched automatically if it exits
- controller, agent, and local display endpoints are healthy after reboot

The only remaining follow-up is a human glance at the physical monitor to close the last gap between "remote runtime is correct" and "the panel visibly shows the intended UI instead of a gray desktop."
