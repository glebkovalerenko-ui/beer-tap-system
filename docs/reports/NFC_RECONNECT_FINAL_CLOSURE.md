# NFC Reconnect Final Closure

## 1. Problem recap

`Admin App` previously lost NFC usability after a physical NFC reader unplug/replug cycle. The app kept running, but card reads did not recover until a full app restart recreated the PC/SC runtime context.

## 2. RCA summary

The root cause was a long-lived `pcsc::Context` without a proper reader lifecycle manager, topology monitoring, or bounded recovery path. After hot unplug/replug, the app could remain attached to stale runtime state and never re-enter a valid ready state on its own.

## 3. Implemented solution

The task was solved by introducing `ReaderManager` inside the Tauri layer and by separating reader lifecycle state from raw card-read commands.

Implemented behavior:

- monitor reader topology with `get_status_change(...)` and `\\?PnP?\\Notification`
- classify disconnected vs recovering vs ready states explicitly
- recreate invalid PC/SC context with bounded backoff
- preserve existing `card-status-changed` compatibility for UI flows
- expose `reader-state-changed` and `get_nfc_reader_state` for frontend bootstrap and recovery UX

## 4. Flicker fix summary

The disconnected-state UI flicker was traced to repeated `disconnected -> scanning -> disconnected` emissions on timeout without a real topology change.

The fix:

- suppresses timeout-driven fake topology transitions
- deduplicates repeated reader lifecycle payloads
- debounces transient frontend state churn after disconnect/recovering events

Result: disconnected and recovering states now remain visually stable.

## 5. Manual hardware verification result

Manual Windows verification with real hardware confirmed the following:

- app works normally when the reader is connected
- unplug does not freeze the app
- UI clearly shows reader disconnected state
- read attempts during disconnect show the correct disconnected-reader message
- replug restores operation without restarting the app
- UID reads succeed again after reconnect
- flicker is eliminated in the disconnected state

## 6. Final merge decision

The branch is suitable for merge into `master` because:

- it is based on current `origin/master`
- it contains only NFC reconnect / flicker-fix / documentation changes
- manual hardware verification is complete
- pre-merge validation commands are expected to be green on the branch before merge

## 7. Remaining non-blocking debt

- A command fired exactly during the physical reconnect window can still require a retry.
- Hardware hot-plug remains a manual verification concern; it is not fully reproducible in CI.
- Multi-reader policy still selects one active reader at a time.

These items do not block production use or closure of the reconnect task.

## 8. Statement

`NFC reconnect task is closed`
