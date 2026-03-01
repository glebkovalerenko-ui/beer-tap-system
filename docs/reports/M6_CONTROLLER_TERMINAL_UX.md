# M6 Controller Terminal UX Verification

## Scope
- Improve controller terminal readability without changing M4/M6 business invariants.
- Deduplicate repetitive controller logs with state-aware reminders.
- Show realtime local pour progress in terminal from flow sensor data only.
- Keep API contracts unchanged. Progress stays local to the controller terminal.

## Changed Runtime Behavior
- `CARD_MUST_BE_REMOVED: remove card to continue.` is logged once on state entry and then only as a reminder.
- `Tap is in processing_sync: unsynced pour exists, blocking new pour start.` is logged once when the tap becomes blocked and then only as a reminder.
- `processing_sync: pending_records=N` is logged once per pending-count change and then only as a reminder.
- Active pour prints terminal progress in realtime:
  - `Pouring: <current_volume_ml> ml / <max_volume_ml> ml | est. cost: <estimated_cost_cents> cents`
  - live single-line redraw on TTY terminals
  - stable line-by-line fallback on non-TTY output such as journald captures
- When the session ends, terminal prints:
  - `Session finished. Poured: X ml`
- Denied authorize paths do not start progress output.

## Invariants Preserved
- `processing_sync` still blocks new pour start.
- `lost_card` deny still forces `CARD_MUST_BE_REMOVED`.
- `insufficient_funds` deny still forces `CARD_MUST_BE_REMOVED`.
- Authorized pour still clamps at `max_volume_ml`.
- No extra backend polling was added for progress or ETA.

## Local Verification Commands
Run from repository root before pushing:

```bash
python -m pytest rpi-controller/test_pour_session.py rpi-controller/test_log_throttle.py rpi-controller/test_terminal_progress.py rpi-controller/test_flow_manager.py
python scripts/encoding_guard.py --all
```

Expected:
- `8 passed`
- `[encoding_guard] OK: no UTF-8/mojibake/bidi-control issues found.`

## Hardware Verification Checklist
Preconditions:
- Backend is running and reachable by the Raspberry Pi controller.
- Controller has valid `.env` / `config.py` values for backend URL and internal token.
- NFC reader, valve relay, and flow sensor are connected.
- There is one visit/card pair with enough funds and one visit/card pair below `min_start_ml`.
- Controller is started with:

```bash
cd rpi-controller
python main.py
```

### A. Authorize OK starts realtime progress
1. Present a card with sufficient funds and valid active visit.
2. Confirm terminal logs a single authorize success line with `max_volume_ml`.
3. Start pouring and watch terminal output.
4. Confirm progress updates in realtime and volume increases locally from the flow sensor.
5. Confirm progress shows `current_volume_ml` and `max_volume_ml`.
6. If `price_per_ml_cents` is returned, confirm estimated cents are shown and increase with volume.

Expected:
- Progress is visible while valve is open.
- TTY terminal rewrites one line instead of spamming many lines.
- Non-TTY output prints at a stable reduced rate, not every loop tick.

### B. Clamp closes at authorized max volume
1. Use a card whose authorize response returns a small known `max_volume_ml`.
2. Keep card on reader and pour until the clamp triggers.
3. Watch terminal output near the limit.

Expected:
- Progress reaches the authorized limit.
- Terminal logs `Valve closed by authorized volume clamp at <max_volume_ml> ml`.
- Final terminal line is `Session finished. Poured: <max_volume_ml> ml`.
- Local DB pour row stores the clamped volume, not a larger value.

### C. Deny does not start progress
1. Present a card that should be denied with `insufficient_funds`.
2. Keep the card on the reader for at least 5 seconds.
3. Repeat with a `lost_card` scenario if available.

Expected:
- Terminal shows deny logs and `CARD_MUST_BE_REMOVED` state.
- No `Pouring: ...` progress lines appear.
- Repeated deny handling does not flood the terminal every loop tick.

### D. processing_sync does not spam
1. Create an unsynced pour in local SQLite so the tap stays blocked by `processing_sync`.
2. Keep controller running for at least 15 seconds.
3. Optionally hold a card on the reader during the blocked period.

Expected:
- Terminal logs `processing_sync` state transition immediately.
- Reminder lines appear only occasionally, not every controller loop.
- If a card is held on the reader, `CARD_MUST_BE_REMOVED` is entered once and reminder logs stay throttled.

### E. Session finish is consistent for other stop reasons
1. Start an allowed pour and remove the card manually before clamp.
2. Start another allowed pour and stop flow to force timeout if your hardware setup supports it.

Expected:
- Every started session ends with `Session finished. Poured: X ml`.
- Progress line stops cleanly after valve close.
- No stale live progress line remains after the session ends.

## Manual Log Signals To Watch
- Good:
  - `Authorize OK for card ... Opening valve with max_volume_ml=...`
  - `Pouring: ...`
  - `Valve closed by authorized volume clamp at ... ml`
  - `Session finished. Poured: ... ml`
- Good but throttled:
  - `CARD_MUST_BE_REMOVED: remove card to continue. reason=...`
  - `Tap is in processing_sync: unsynced pour exists, blocking new pour start.`
  - `processing_sync: pending_records=...`
- Should not happen:
  - the same line printed every 100 ms while state is unchanged
  - progress output during denied authorize

## Notes
- Progress is derived only from local flow sensor pulses and local authorize data.
- This report verifies UX behavior only. It does not redefine controller/backend API contracts.
