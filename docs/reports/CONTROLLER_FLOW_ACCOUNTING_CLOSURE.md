## 1. Goal

Close the accounting gap between controller live-flow telemetry and backend liquid accounting:

- tail flow after valve close must stay inside the same sale pour;
- flow outside a valid sale session must never become a `pour`;
- operators must be able to see sale flow, non-sale flow, and total physical flow separately.

## 2. Problem Summary

Before this closure work, controller flow visibility and backend accounting were only partially connected:

- `controller_flow_event` existed for audit and live-feed visibility;
- `pours` remained the only durable accounting source for liquid depletion;
- closed-valve flow, no-card flow, and anomalous flow could be visible but not fully reflected in keg remainder accounting;
- there was no first-class non-sale accounting record.

This created a bad state where physical liquid could leave the keg without being fully represented in accounting totals.

## 3. Model Decision

The closure keeps the existing architecture and adds a missing accounting fact:

- `pours` remain the sale record:
  - tied to guest/card/visit;
  - charges balance;
  - contributes to sale volume.
- `non_sale_flows` store non-sale liquid movement:
  - keyed by `event_id` for idempotent updates;
  - classified by `flow_category`, `session_state`, and `reason`;
  - never upgraded into a `pour`.

Controller flow events still emit `started`, `updated`, and `stopped`. The backend interprets them as follows:

- `authorized_session` -> visibility only, final accounting still closes through `pours`;
- any other session state -> `non_sale_flows` accounting path.

## 4. Keg Accounting

Keg depletion now reflects all real liquid movement:

- sale flow depletes keg volume through the synced `pour`;
- non-sale flow depletes keg volume through `non_sale_flows`;
- non-sale updates are applied by delta, so repeated `updated` events do not double-count;
- if a keg reaches zero, keg/tap state still transitions to `empty`.

## 5. Reporting and UI

`GET /api/reports/flow-summary` is the accounting read model for this feature. It returns:

- `sale_volume_ml`
- `non_sale_volume_ml`
- `total_volume_ml`
- `non_sale_breakdown`
- per-tap breakdowns

Admin UI consumes this endpoint to show:

- sale flow
- non-sale flow
- total flow
- non-sale anomaly categories such as closed-valve flow or flow without card

## Final Architecture

- Controller emits flow events for both authorized and anomalous liquid movement.
- Backend stores:
  - sale completion in `pours`
  - non-sale liquid in `non_sale_flows`
- Live feed remains a visibility stream.
- `flow-summary` is the accounting projection.

## Data Flow Diagram

```text
Authorized pour path
controller flow events -> audit/live feed
controller sync pour -> pours -> keg depletion -> sale totals

Non-sale flow path
controller flow events -> audit/live feed -> non_sale_flows -> keg depletion -> non-sale totals
```

## Accounting Guarantees

- `non_sale_flows` reduce keg volume.
- `non_sale_flows` never create a `pour`.
- `authorized_session` flow events do not create `non_sale_flows`.
- tail flow stays inside the same sale pour through `tail_volume_ml`.
- `total_volume_ml = sale_volume_ml + non_sale_volume_ml`.

## Verification Results

Verification for closure includes:

- encoding repair in:
  - `rpi-controller/flow_manager.py`
  - `rpi-controller/sync_manager.py`
- command results:
  - `python scripts/encoding_guard.py --all` -> passed
  - `python -m pytest backend -q` -> 108 passed, 5 skipped
  - `python -m pytest rpi-controller -q` -> 13 passed, 1 skipped (`test_hw.py` skips when GPIO/smartcard libraries are unavailable)
  - `npm run build` in `admin-app` -> passed
  - `cargo check` in `admin-app/src-tauri` -> passed
- backend tests proving:
  - authorized sale flow creates a synced pour, reduces keg volume, and does not create `non_sale_flows`
  - authorized tail flow stays on the same pour and does not create `non_sale_flows`
  - no-card flow creates `non_sale_flows`, does not create a pour, and reduces keg volume
  - `GET /api/reports/flow-summary` returns consistent sale, non-sale, and total totals
- controller/live-feed tests proving:
  - latest snapshot deduplication by `event_id`
  - non-sale delta aggregation on repeated updates
- performance sanity checks:
  - non-sale accounting updates a single `non_sale_flows` row per `event_id` instead of creating duplicate accounting rows
  - live feed resolves one latest snapshot per `event_id`, so repeated controller updates do not surface as duplicate active items
  - audit logging still records each incoming flow event, which is acceptable for closure but remains the main write-amplification point

## Remaining Known Limitations

- `flow-summary` is currently aggregate accounting, not shift-scoped accounting.
- audit logging still writes one row per emitted flow event, so event rate directly affects audit write volume.
- this closure does not redesign the protocol; it stabilizes the current controller-to-backend accounting model.
