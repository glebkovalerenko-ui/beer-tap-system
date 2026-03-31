# Operational Model v1

Date: 2026-03-10
Scope: frozen M1-M7 operational core

This document focuses on runtime invariants. For the full system overview, start with `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`.

## 1. Core operational principles

- `Visit` is the center of service operations.
- Backend is the source of truth for operational state.
- Controller measures factual volume and duration, but not official timestamps.
- Shift state gates operational work.
- POS is outside the core operational path for this stage.

## 2. Main invariants

### Visit

- one guest can have only one active visit;
- one card can belong to only one active visit at a time;
- a visit may open without a card;
- active visit close is blocked while unresolved `pending_sync` exists.

### Card

- card assignment is separate from visit open;
- active visit card becomes `active`;
- closing the visit deactivates the card;
- `card_returned=true` also clears guest binding.

### Shift

- only one open shift exists;
- no open shift means:
  - no visit open;
  - no pour authorize;
  - no top-up or refund.

### Pour

- authorize creates or reuses exactly one backend `pending_sync` row for the visit/tap pair;
- finalization ends in one of:
  - `synced`
  - `reconciled`
  - `rejected`
- late sync after manual reconcile is audit-only;
- duplicate sync must not double charge.

## 3. Visit lifecycle

1. Register or find guest.
2. Open visit.
3. Optionally assign/bind card.
4. Top up balance if needed.
5. Controller authorizes and performs pours.
6. Reconcile unresolved pours if needed.
7. Close visit and deactivate card.

## 4. Pour lifecycle

### Authorize stage

- Controller requests `POST /api/visits/authorize-pour`.
- Backend checks lost-card state, active visit, active tap lock, tap configuration, shift gate, and balance/clamp policy.
- On success backend:
  - sets `visit.active_tap_id`;
  - sets `visit.lock_set_at`;
  - moves tap to `processing_sync`;
  - creates or reuses one `pending_sync` row.

### Sync stage

- Controller later submits `/api/sync/pours`.
- If a matching pending row exists and business checks pass, backend:
  - writes factual amount/volume/duration;
  - moves row to `synced`;
  - clears visit lock;
  - returns tap to `active` unless keg is empty.

### Manual reconcile stage

- Operator uses `POST /api/visits/{visit_id}/reconcile-pour`.
- Backend finalizes the pour as `reconciled`, updates balance/keg state, clears lock, and keeps the flow idempotent by `visit_id + short_id`.

### Rejected stage

- If a previously authorized sync cannot be safely charged, backend marks the pending row as `rejected` and clears stale lock/tap state.

## 5. Lost card model

- Lost cards live in a dedicated registry.
- Authorize for lost cards is hard-denied with `reason="lost_card"`.
- Operator can report lost card from an active visit, then resolve it in the visit workspace by reissue, cancel-lost, or service-close.
- Generic lost-card restore remains for ordinary inventory-lost cards and does not replace visit recovery.
- NFC resolve endpoint provides a single operator lookup path.

## 6. FIFO keg recommendation

- Current schema uses `beverage_id` as the practical beer-type key.
- FIFO recommendation is suggestion-only.
- Eligible stock is:
  - same `beverage_id`
  - `status = full`
  - `current_volume_ml > 0`
  - not already assigned to a tap
- Ordering is deterministic:
  - `created_at ASC`
  - `keg_id ASC`

## 7. Reports and time policy

- X report is computed, not persisted.
- Z report is persisted and idempotent.
- Report time windows use DB time only.
- Backend official timestamps are DB-authored only.

## 8. POS-ready boundary

Current stage includes:

- `notify_topup`
- `notify_refund`
- `notify_pour`

Current stage does not include:

- `notify_open_visit`
- `notify_close_visit`
- `visit.pos_order_id`
- real POS transport or retry/outbox delivery
