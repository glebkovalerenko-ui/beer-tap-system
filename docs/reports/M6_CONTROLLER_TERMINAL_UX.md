# M6 Controller Terminal UX Verification

## Scope
- Improve controller terminal readability without changing current `origin/master` authorize or clamp contracts.
- Deduplicate repetitive controller logs with a reusable state-aware throttle.
- Show realtime local pour progress in the terminal using local flow sensor data only.
- Keep API contracts unchanged in this PR.

## Runtime Behavior Changed In This PR
- `CARD_MUST_BE_REMOVED: remove card to continue.` is logged once on state entry and then only as a reminder.
- `Tap is in processing_sync: unsynced pour exists, blocking new pour start.` is logged once on block entry and then only as a reminder.
- `processing_sync: pending_records=N` is logged once per pending-count change and then only as a reminder.
- During an active pour, the terminal shows local realtime progress:
  - `Pouring: <current_volume_ml> ml | est. cost: <estimated_cost_cents> cents`
  - on TTY terminals the same row is redrawn with carriage return
  - on non-TTY output the controller falls back to periodic full lines
- When the session ends, the terminal prints:
  - `Session finished. Poured: X ml`
- Denied authorize paths do not start progress output.

## Explicitly Not In Scope
- No changes to authorize response contract.
- No changes to clamp logic or `max_volume_ml`.
- No `pour_session.py` helpers.
- No controller/backend API contract additions.

## Local Verification Commands
Run from repository root:

```bash
python -m pytest rpi-controller/test_log_throttle.py rpi-controller/test_terminal_progress.py rpi-controller/test_flow_manager.py
python scripts/encoding_guard.py --all
```

Expected:
- `6 passed`
- `[encoding_guard] OK: no UTF-8/mojibake/bidi-control issues found.`

## Hardware Verification Checklist
Preconditions:
- Backend is running and reachable by the Raspberry Pi controller.
- Controller has valid backend URL and internal token.
- NFC reader, valve relay, and flow sensor are connected.
- At least one valid active card exists.
- At least one card or visit exists that will be denied.

Start controller:

```bash
cd rpi-controller
python main.py
```

### A. Authorize OK starts realtime progress
1. Present a valid card with an active visit.
2. Confirm terminal logs a single authorize success line.
3. Start pouring and watch terminal output.
4. Confirm `Pouring: X ml | est. cost: Y cents` updates while flow sensor pulses are arriving.

Expected:
- Active pour progress is visible in realtime.
- TTY terminal redraws a single status row.
- Non-TTY output prints reduced-rate progress lines instead of one line per loop tick.

### B. Session completion prints final line
1. Start an allowed pour.
2. Remove the card before timeout.

Expected:
- Terminal stops progress output.
- Final terminal line is `Session finished. Poured: X ml`.
- Local DB record volume matches the accumulated flow-sensor total.

### C. Deny does not start progress
1. Present a card that will be denied.
2. Keep the card on the reader for at least 5 seconds.

Expected:
- Deny logs appear.
- No `Pouring: ...` lines appear.
- Repeated wait handling does not flood the terminal.

### D. processing_sync does not spam
1. Prepare an unsynced local pour so the tap stays in `processing_sync`.
2. Leave the controller running for at least 15 seconds.
3. Optionally hold a card on the reader during the blocked period.

Expected:
- `processing_sync` entry is logged immediately.
- Reminder lines appear only occasionally.
- `CARD_MUST_BE_REMOVED` reminder logs stay throttled as well.

## Notes
- Progress in this PR is derived only from local flow sensor pulses and local controller pricing config.
- If future work adds server-authorized `max_volume_ml` or per-pour price data to master, `TerminalProgressDisplay` already supports rendering optional max/cost fields without changing its terminal behavior.
