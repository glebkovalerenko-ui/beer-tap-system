# API Reference

Date: 2026-03-10
Scope: practical API contract for the frozen M1-M7 stage

This document focuses on the endpoints and response semantics that matter for current operations. Exact request and response models live in `backend/schemas.py` and the FastAPI OpenAPI schema.

## 1. Base URL

```text
http://localhost:8000
```

## 2. Authentication

### Admin and operator calls

- `POST /api/token`
- use `Authorization: Bearer <token>`

### Controller calls

- use `X-Internal-Token: <token>`
- controller primarily calls:
  - `POST /api/visits/authorize-pour`
  - `POST /api/sync/pours`
  - `GET /api/system/status`

## 3. Health and runtime

### `GET /`

- basic backend smoke endpoint
- expected response: HTTP `200`

### `GET /api/system/status`

- startup and emergency-stop probe
- expected response: HTTP `200`

### `GET /api/system/states/all`

- diagnostic endpoint for system state flags

## 4. Shift endpoints

### `POST /api/shifts/open`

- opens the only allowed active shift

### `POST /api/shifts/close`

- closes current shift
- blocked by:
  - active visits
  - unresolved `pending_sync` pours

### `GET /api/shifts/current`

- returns current shift state

### Reports

- `GET /api/shifts/{shift_id}/reports/x`
- `POST /api/shifts/{shift_id}/reports/z`
- `GET /api/shifts/{shift_id}/reports/z`
- `GET /api/shifts/reports/z?from=YYYY-MM-DD&to=YYYY-MM-DD`

## 5. Guest, card, and visit operations

### Guests

- `POST /api/guests`
- `GET /api/guests`
- `GET /api/guests/{guest_id}`
- `PUT /api/guests/{guest_id}`

### Top-up and refund

- `POST /api/guests/{guest_id}/topup`
- `POST /api/guests/{guest_id}/refund`

Operational notes:

- both require an open shift;
- both write `Transaction` rows;
- both emit POS stub notifications.

### Cards

- `POST /api/cards/`
- `GET /api/cards/`
- `GET /api/cards/{card_uid}/resolve`
- `PUT /api/cards/{card_uid}/status`

`GET /api/cards/{card_uid}/resolve` is the unified operator lookup path for:

- lost card recovery;
- active visit lookup;
- guest-bound card with no active visit;
- unknown card handling.

## 5A. Operator projections

### `GET /api/operator/today`

Purpose:

- operator-first route projection for the `Today` screen;
- bundles current shift, KPI, flow summary, system health, incidents, live feed, and actionable attention items.

Expected top-level fields:

- `generated_at`
- `current_shift`
- `today_summary`
- `flow_summary`
- `feed_items`
- `system_health`
- `incidents`
- `attention_items`
- `priority_cta_source`

### `GET /api/operator/taps`

Purpose:

- operator workspace projection for the tap grid;
- enriches each tap with subsystem status, active-session context, sync state, recent events, and action-policy metadata.

Expected per-tap fields include:

- `tap_id`
- `display_name`
- `status`
- `keg`
- `display_enabled`
- `controller_status`
- `display_status`
- `reader_status`
- `sync_state`
- `last_heartbeat_at`
- `active_session`
- `recent_events`
- `safe_actions`

### `GET /api/operator/taps/{tap_id}`

Purpose:

- operator drawer/detail projection for a single tap.

Notes:

- extends the tap workspace card with `history_items`;
- used by the tap drawer to refresh one selected tap without reloading the whole workspace.

### `GET /api/operator/cards/lookup?query=...`

Purpose:

- operator-first lookup contract for `Cards & Guests`;
- returns the card/guest/visit decision context already shaped for the operator workflow.

Expected top-level fields:

- `card_uid`
- `is_lost`
- `lost_card`
- `active_visit`
- `guest`
- `card`
- `recommended_action`
- `recent_events`
- `last_tap_label`
- `lookup_summary_items`
- `allowed_quick_actions`

### Visits

- `POST /api/visits/open`
- `POST /api/visits/{visit_id}/assign-card`
- `POST /api/visits/{visit_id}/close`
- `POST /api/visits/{visit_id}/force-unlock`
- `POST /api/visits/{visit_id}/report-lost-card`
- `POST /api/visits/{visit_id}/reconcile-pour`
- `GET /api/visits/active`
- `GET /api/visits/active/by-card/{card_uid}`
- `GET /api/visits/active/by-guest/{guest_id}`
- `GET /api/visits/active/search?q=...`

Important visit rules:

- one active visit per guest;
- one active visit per card;
- visit close fails with `409 pending_sync_exists_for_visit` while unresolved pending exists.

## 6. Pour authorize and controller sync

### `POST /api/visits/authorize-pour`

Purpose:

- backend validates business rules before valve open;
- backend creates or reuses one `pending_sync` record;
- backend returns the controller clamp contract.

Success response includes:

- `allowed`
- `min_start_ml`
- `max_volume_ml`
- `price_per_ml_cents`
- `balance_cents`
- `allowed_overdraft_cents`
- `safety_ml`
- `lock_set_at`
- visit payload

Common deny reasons:

- `shift_closed`
- `lost_card`
- `insufficient_funds`
- `no_active_visit`
- `card_in_use_on_other_tap`
- `tap_not_configured`

### `POST /api/sync/pours`

Purpose:

- finalize factual pours from controller local queue.

Per-pour payload fields:

- `client_tx_id`
- `short_id`
- `card_uid`
- `tap_id`
- `duration_ms`
- `volume_ml`
- `price_cents`

Legacy `start_ts` and `end_ts` are accepted only as fallback for duration derivation.

#### Result statuses

- `accepted`
- `audit_only`
- `rejected`
- `conflict`

#### Important outcomes

- `pending_updated_to_synced`
- `duplicate_existing`
- `audit_late_matched`
- `audit_late_recorded`
- `audit_missing_pending`
- `rejected_insufficient_funds`
- `rejected_tap_mismatch`

Operational meaning:

- `accepted`: factual pour finalized operationally.
- `audit_only`: recorded for audit only; no operational charge.
- `rejected`: terminal invalid finalization for the pending row.
- `conflict`: hard tap/lock conflict.

## 7. Lost card endpoints

- `POST /api/lost-cards`
- `GET /api/lost-cards`
- `POST /api/lost-cards/{card_uid}/restore`

Lost-card rule:

- authorize for a lost card returns `403` with `detail.reason="lost_card"`.

## 8. Kegs, taps, beverages, controllers

### Kegs

- `POST /api/kegs/`
- `GET /api/kegs/`
- `GET /api/kegs/{keg_id}`
- `PUT /api/kegs/{keg_id}`
- `DELETE /api/kegs/{keg_id}`
- `GET /api/kegs/suggest?beer_type_id=<uuid>`

FIFO recommendation semantics:

- maps `beer_type_id` to current `beverage_id`;
- returns recommendation only;
- does not mutate tap or keg state.

### Taps

- `POST /api/taps/`
- `GET /api/taps/`
- `GET /api/taps/{tap_id}`
- `PUT /api/taps/{tap_id}`
- `DELETE /api/taps/{tap_id}`
- `PUT /api/taps/{tap_id}/keg`
- `DELETE /api/taps/{tap_id}/keg`

### Beverages

- `POST /api/beverages/`
- `GET /api/beverages/`
- `GET /api/beverages/{beverage_id}`

### Controllers

- `POST /api/controllers/register`
- `GET /api/controllers/`

## 9. Audit and pours read APIs

- `GET /api/audit/`
- `GET /api/pours/`

These are operational read endpoints used for inspection, support, and verification.

## 10. Time and POS notes

- Official backend timestamps are authored by Postgres DB time.
- Controller sends volume and duration facts, not official timestamps.
- Top-up, refund, and finalized pour currently trigger POS stub audit/log events.
- Visit open/close POS hooks and durable POS order mapping are intentionally not implemented yet.
