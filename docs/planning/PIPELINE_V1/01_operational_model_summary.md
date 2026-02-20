# Operational Model V1 — Structured Summary

Source: `docs/architecture/OPERATIONAL_MODEL_V1.md`.

## 1) Domain entities and constraints

## 1.1 Core entities
- **Location**: `id`, `name`, `timezone`.
- **Guest**: identity + compliance attributes (`passport_*`, `birth_date`, `consent_number`), activity fields, block flag.
- **Visit**: per-bar-session aggregate (`guest_id`, `card_uid`, `active_tap_id`, status lifecycle, open/close timestamps + reason).
- **LostCard**: independent registry for lost UID events (`card_uid`, `guest_id`, `visit_id`, `reported_by`).
- **BeerType**: catalog (`name`, `style`, `price_per_ml`, `is_active`).
- **Keg**: physical inventory unit with lifecycle timestamps and remaining volume.
- **Tap**: hardware endpoint with operational status incl. `processing_sync`.
- **PourSession**: immutable pour fact with linkage to visit/tap/keg and sync lifecycle.
- **Shift / ShiftMember**: operational period and staff participation records.
- **Alert**: operational incident model with severity + acknowledgement/resolution metadata.

## 1.2 Key constraints from spec
- Guest passport must be unique; under-18 cannot receive card.
- One guest can have only one active visit.
- Active visit maps to one active card at a time.
- Closing a visit deactivates card.
- Active visits block shift closure.
- Lost card UID usage must trigger block + critical alert.
- Controller is source of truth for pour volume.

## 2) State machines

## 2.1 Visit state machine
- `active` → `closed` (with `closed_reason`, `closed_at`).
- Guards:
  - cannot open if guest already has active visit;
  - card must map to active visit;
  - shift closure blocked while any visit active.

## 2.2 Tap state machine
- `active`
- `processing_sync` (during post-offline reconciliation)
- `out_of_keg`
- `maintenance`
- `error`

Key transition examples:
- `active` → `processing_sync` when connection lost mid-pour and pending sync exists.
- `processing_sync` → `active` once sync succeeds and visit unlock (`active_tap_id` clear) is complete.
- `active` → `out_of_keg` when keg depleted.

## 2.3 PourSession state machine
- Session lifecycle: started → ended.
- Sync lifecycle field: `sync_status` = `pending_sync` or `synced`.
- Offline flow requires local completion + later server reconciliation.

## 2.4 Shift state machine
- `opened` → `closed` (single shift across staff rotation).
- Closure wizard gates:
  1. no active visits,
  2. no pending sync,
  3. unresolved alerts shown,
  4. equipment inspection confirmation,
  5. summary view,
  6. final confirmation.

## 3) Core workflows

## 3.1 Visit open/close
1. Guest register/lookup.
2. Age verification.
3. External POS financial operation.
4. System opens Visit and assigns card.
5. Visit close deactivates card and records reason.

## 3.2 Pour authorization
Before allowing pour:
- visit active,
- card matches visit,
- card not in LostCard,
- `active_tap_id` is null,
- balance >= minimum pour threshold.

If valid:
- lock visit to tap (`active_tap_id = tap_id`),
- transfer balance context to controller,
- start pour session.

## 3.3 Simultaneous usage prevention
- If `active_tap_id != null`: deny with explicit tap message and log event.

## 3.4 Offline and sync recovery
- Mid-pour disconnect: continue locally, mark `pending_sync`, tap -> `processing_sync`, block new cards.
- Recovery: controller submits final volume; backend reconciles, clears lock, returns tap to active.
- Manual mismatch requires `BalanceMismatch` alert.

## 3.5 Keg replacement (FIFO)
- On empty keg: tap -> `out_of_keg`.
- Suggest next keg by FIFO rule: same BeerType + `warehouse` + oldest `received_at`.
- Staff confirms replacement; keg -> `connected`; tap -> `active`.

## 3.6 Shift closing wizard
- Gate checks + non-blocking critical alerts (must acknowledge, need not resolve before closure).

## 4) Integration boundary

## POSAdapter contract
- `notify_topup(guest, amount)`
- `notify_refund(guest, amount)`
- `notify_pour(guest, amount, beer_type)`

Principle: core domain remains POS-independent; MVP supports semi-manual synchronization.

## 5) System requirements derived from spec

## 5.1 Functional requirements (MVP-must)
1. Visit lifecycle with single-active-visit invariant.
2. Tap control with active-tap lock semantics.
3. PourSession persistence with sync-status (`synced`/`pending_sync`).
4. Offline pour continuation + deferred sync processing.
5. LostCard registry + enforcement at authorization time.
6. Keg lifecycle + FIFO recommendation for replacement.
7. Shift model + closure wizard checks.
8. Alert model with severity, acknowledge, resolve.
9. Audit logging for sensitive/operational actions.
10. POS integration boundary interface (contract defined, deep adapter can be minimal in MVP).

## 5.2 Non-functional requirements (MVP-must)
- Operational reliability under intermittent connectivity.
- Deterministic sync reconciliation behavior.
- Event/audit traceability for key state changes.
- Clear source-of-truth boundaries (controller for volume; backend for canonical operational state).

## 5.3 Deferred requirements
- Internal fiscal module.
- Multi-location runtime expansion (model-ready now).
- Advanced card cryptography.
- Sensor-heavy keg automation (weight sensors).
- Complex warehouse accounting.
- Inactivity fee logic.
- Advanced role hierarchy beyond unified staff role.
