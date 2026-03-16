# Processing Sync Recurrence After Option B RCA

## 1. Problem statement

After the Option B zero-volume fix had already been implemented in a dedicated code line, manual verification on the real Tap Display still reproduced the same on-screen service state:

- `Сервисное состояние`
- `Подождите`
- `Кран завершает синхронизацию`
- `processing_sync`

The investigation goal was to prove whether this was:

- a true zero-volume authorize-abort recurrence,
- the same old contract gap,
- an incomplete Option B implementation,
- or a different path that only looked similar.

## 2. Reproduction conditions

The live reproduction on Raspberry Pi Tap 1 was:

1. Present card `0b24b1cd`.
2. Authorize pour successfully.
3. Remove the card.
4. Do not produce a factual pour.
5. Observe that the display returns to backend-driven `processing_sync`.

Relevant timestamps from the reproduced incident:

- `2026-03-16 17:59:03+03:00` Pi controller log: authorize accepted for card `0b24b1cd`.
- `2026-03-16 17:59:10+03:00` Pi controller log: valve closed with `reason=card_removed`.
- Same session ended with `Налито: 0 мл`.

## 3. Live evidence collected

### Raspberry Pi (`cybeer@192.168.0.114`)

- Deployed repo SHA at reproduction time:
  - branch `hotfix/tap-display-kiosk-reboot`
  - commit `a93f4a72763d55ce01e7a7e83a7561732a9133d5`
- Controller runtime after the incident:
  - `/run/beer-tap/display-runtime.json` reported `phase="idle"`
  - `GET /local/display/runtime` also reported `runtime.phase="idle"`
- Display bootstrap snapshot after the incident:
  - `GET /local/display/bootstrap` still reported `snapshot.tap.status="processing_sync"`
- Local journal state:
  - `local_journal.db` contained `total_rows=0`
  - `unsynced_for_tap1=0`
  - no local pour artifact existed for the reproduced session
- Controller logs around the reproduced session:
  - `2026-03-16 17:59:03+03:00` authorize accepted for card `0b24b1cd`, limit `98 мл`
  - repeated progress remained `Налив: 0 мл из 98 мл`
  - `2026-03-16 17:59:10+03:00` `Клапан закрыт: причина=card_removed`
  - `Сессия завершена. Налито: 0 мл`

### Backend / hub (`cybeer@192.168.0.110`)

- Deployed repo SHA at investigation time:
  - branch `feature/tap-display-real-pi-bringup`
  - commit `3256c6cd0c232ead70cc1779f1bea5de10b07201`
- Backend snapshot visible to display:
  - `tap_id=1`
  - `tap.status='processing_sync'`
- Live DB state after reproduction:
  - `taps.tap_id=1 status='processing_sync'`
  - active visit `d68bac03-42b3-4105-81f4-e18327d16785`
  - `visits.active_tap_id=1`
  - `visits.lock_set_at='2026-03-16 14:59:02.906008+00'`
  - fresh backend row:
    - `client_tx_id='pending-sync:d68bac03-42b3-4105-81f4-e18327d16785:1:797dfc08'`
    - `card_uid='0b24b1cd'`
    - `tap_id=1`
    - `volume_ml=0`
    - `sync_status='pending_sync'`
    - `authorized_at='2026-03-16 14:59:02.906008+00'`
- Backend logs for the same incident:
  - `2026-03-16 14:59:03.039 UTC`
  - `authorize_pour ... actor=internal_rpi card_uid=0b24b1cd tap_id=1 visit_id=d68bac03-42b3-4105-81f4-e18327d16785 outcome=pending_created`

### Contract-line comparison evidence

- Option B code line exists in the repo as:
  - code commit `b4de59db8d1108bb1d0dd63fb197a9c3e49d60c4`
  - report commit `04bb5079c1dffd3b545fc3eaea0b16aef2cd33d5`
- Ancestry check proved that neither live node contained the Option B code commit:
  - Pi SHA `a93f4a7...` does **not** contain `b4de59d`
  - hub SHA `3256c6c...` does **not** contain `b4de59d`
- In the pre-Option-B authorize path, backend still created durable pending during authorize.
- In the Option B line, authorize only sets the lock, while durable pending starts later via `POST /api/visits/register-pending-pour` and zero-volume exits via `POST /api/visits/release-pour-lock`.

## 4. Expected behavior after Option B

After Option B, the contract is:

1. `POST /api/visits/authorize-pour` only acquires the visit lock and returns clamp data.
2. The controller decides whether a factual local pour artifact exists using its existing persistence threshold:
   - `total_volume_ml > 1` means a durable local artifact exists
   - `total_volume_ml <= 1` means no durable local artifact exists
3. That threshold is evaluated after post-close tail collection, so final branch selection already includes any captured tail.
4. Therefore both zero-volume stop reasons must behave the same:
   - `card_removed` with final `total_volume_ml <= 1` -> `release-pour-lock`
   - `flow_timeout` with final `total_volume_ml <= 1` -> `release-pour-lock`
5. No durable backend `pending_sync` should exist for those `<= 1 мл` sessions.
6. Backend must not move Tap 1 into `processing_sync` for those sessions.

This threshold is not a business rule about authorization. It is the controller's durable-artifact boundary for deciding whether there is any factual pour record to synchronize at all.

## 5. Actual behavior

The reproduced incident followed the old contract, not the Option B contract:

1. Controller authorized the pour.
2. Final measured volume stayed `0 мл`.
3. Card removal closed the valve.
4. No local journal row was created on Pi.
5. Backend still created durable `pending_sync` during authorize.
6. Backend kept:
   - `visits.active_tap_id=1`
   - `visits.lock_set_at`
   - `taps.status='processing_sync'`
7. Display bootstrap honestly rendered `processing_sync` from backend snapshot while controller runtime was already `idle`.

This means the system did **not** execute the expected Option B no-pour release path on the live device. It executed the older authorize-created-pending path instead.

## 6. Root cause

The recurrence was the same old zero-volume contract gap, but on an undeployed code line.

Root cause chain:

1. Option B had been implemented in a separate repo line, but the real Pi and hub were still running earlier branches that did not contain commit `b4de59d`.
2. Those live branches still used the old backend authorize contract that created durable `pending_sync` at authorize time.
3. The reproduced hardware session was a true zero-volume authorize-abort:
   - final measured `total_volume_ml=0`
   - stop reason `card_removed`
   - no local artifact persisted
4. Because there was no local artifact, no normal sync payload could ever clear that backend row.
5. Backend `tap.status='processing_sync'` therefore remained legitimate relative to its own stale state, and the display rendered it honestly.

This was **not**:

- a small-tail `> 1 мл` scenario,
- a controller-runtime false positive,
- a display-only mapping bug,
- or proof that the Option B contract itself was incomplete.

It was the same bug shape reproduced on live code that still predated Option B.

## 7. Fix applied or required next fix

### Software alignment applied in this investigation branch

No broader redesign was needed beyond the existing Option B contract.

This investigation branch keeps the Option B runtime behavior and adds explicit regression coverage for the exact threshold boundary:

- `total_volume_ml <= 1` stays on the no-pour release path
- `total_volume_ml > 1` creates/registers durable pending
- the same boundary now has explicit tests for both:
  - `card_removed`
  - `flow_timeout`

### Operational follow-up still required

The software fix intentionally does **not** hide live-row cleanup.

If the currently stuck live row still exists after rollout, one separate audited operational cleanup is still required for:

- `pending-sync:d68bac03-42b3-4105-81f4-e18327d16785:1:797dfc08`

That cleanup must remain outside the software fix and outside normal runtime behavior.

## 8. Post-investigation verification

Verification completed in this branch:

- `python -m pytest backend/tests/test_m4_offline_sync_reconcile.py`
  - `10 passed`
  - covers zero-volume release without durable pending, explicit `1 мл` release semantics, and explicit `2 мл` durable-pending semantics
- `python -m pytest rpi-controller/test_flow_manager.py`
  - `18 passed`
  - covers the same threshold boundary for both `card_removed` and `flow_timeout`, including post-close tail contribution before branch selection
- `python scripts/encoding_guard.py --all`
  - passed with no UTF-8/mojibake/bidi issues
- Option B branch-selection semantics are now explicitly documented in:
  - controller code comment
  - automated tests
  - this RCA

Live deployment verification was **not** performed in this investigation session, so this report does not claim that the already-stuck live row was cleared automatically.

## 9. Final verdict

`ROOT CAUSE IDENTIFIED, FOLLOW-UP FIX STILL NEEDED`

Why:

- the recurrence is fully explained
- it was a true zero-volume authorize-abort
- backend was again the direct source of `processing_sync`
- the reproduced incident came from live nodes still running pre-Option-B code
- repo alignment and regression coverage are ready in this branch
- but live rollout and one-time operational cleanup for the already-stuck row still remain separate follow-up actions
