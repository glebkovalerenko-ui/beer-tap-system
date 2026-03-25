# Admin App Operator Projections Phase 2 Result

Date: 2026-03-25

## Purpose

This document records the implemented result of the Admin App "Operator Projections" increment inside the current repository.

The goal of this phase was to stop composing the operator experience only from scattered CRUD calls and frontend-only derivations, and to introduce operator-first backend projections for the most important live workflows.

This is an implementation handoff note. It is not a new roadmap and it does not claim that all later phases are complete.

## Scope Implemented

This increment was implemented inside the existing `admin-app` shell, existing auth model, and existing Tauri bridge.

In scope:

- backend operator-first projection endpoints for:
  - `Today`
  - `Taps`
  - tap drawer detail
  - `Cards & Guests` lookup
- typed backend schemas for the new operator view-model layer
- Tauri bridge commands for the new operator endpoints
- frontend rewiring so the existing routes consume the new projections
- focused API and smoke verification

Out of scope:

- WebSocket realtime transport
- degraded command queue and replay UI
- full server-side dangerous-action policy contracts
- new management/reporting routes
- replacing all legacy endpoints or all frontend derived models

## Result Summary

The Admin App now has a real operator projection layer instead of relying only on a collection of independent route-level fetches.

The implemented result includes:

- One backend `Today` overview projection bundling shift state, KPI, flow summary, system health, incidents, event feed, and attention items.
- One backend tap workspace projection that enriches each tap with subsystem status, active session context, recent events, sync state, and safe-action metadata.
- One backend tap drawer-detail projection so the drawer can request a single tap-specific operator model.
- One backend card lookup projection that returns operator summary items, recent events, last tap, and allowed quick actions.
- Tauri commands for these projections without creating a second frontend transport path.
- Existing `Today`, `Taps`, and `Cards & Guests` routes switched to the new contracts without changing the shell IA.

## Public Contracts Added

New operator endpoints added:

- `GET /api/operator/today`
- `GET /api/operator/taps`
- `GET /api/operator/taps/{tap_id}`
- `GET /api/operator/cards/lookup?query=...`

New backend schema types added in `backend/schemas.py`:

- `OperatorTodayModel`
- `TapWorkspaceCard`
- `TapDrawerModel`
- `CardGuestContextModel`
- supporting policy and subsystem-status models

These contracts are intentionally operator-first. They bundle the state the route needs now instead of forcing the route to reconstruct everything from multiple low-level API calls.

## Route-by-Route Outcome

### Today

Implemented behavior:

- `pourStore` now consumes `GET /api/operator/today` as the primary source for:
  - `feedItems`
  - `todaySummary`
  - `flowSummary`
  - route-level overview context
- `Today.svelte` keeps its current route structure, but the backing data now comes from one operator overview payload instead of multiple separate reads.

Key files:

- `backend/api/operator.py`
- `backend/crud/operator_crud.py`
- `admin-app/src/stores/pourStore.js`

### Taps

Implemented behavior:

- `tapStore.fetchTaps()` now reads `GET /api/operator/taps`.
- tap cards receive backend-enriched fields for:
  - `active_session`
  - `recent_events`
  - `controller_status`
  - `display_status`
  - `reader_status`
  - `sync_state`
  - `last_heartbeat_at`
  - safe-action policy metadata
- drawer open now asks for `GET /api/operator/taps/{tap_id}` and refreshes the selected tap with the richer drawer model.
- tap mutations still use the legacy mutation endpoints, but the store refreshes the operator detail after mutation so the workspace stays projection-driven.

Key files:

- `backend/api/operator.py`
- `backend/crud/operator_crud.py`
- `admin-app/src/stores/tapStore.js`
- `admin-app/src/routes/TapsWorkspace.svelte`

### Cards and Guests

Implemented behavior:

- card lookup now goes through `GET /api/operator/cards/lookup`.
- lookup result now carries backend-prepared:
  - operator summary items
  - recent events
  - last tap label
  - allowed quick actions
- frontend cards/guests model still preserves existing fallbacks, but it now prefers the backend operator context when available.

Key files:

- `backend/api/operator.py`
- `backend/crud/operator_crud.py`
- `admin-app/src/stores/lostCardStore.js`
- `admin-app/src/lib/operator/cardsGuestsModel.js`

## Backend Design Notes

Implementation approach:

- The new route layer lives in `backend/api/operator.py`.
- Projection assembly lives in `backend/crud/operator_crud.py`.
- Existing domain CRUD remains in place and is reused where practical.
- The new operator layer composes:
  - shift state from `shift_crud`
  - KPI and feed data from `pour_crud`
  - flow summary from `flow_accounting_crud`
  - system health and incidents from `incident_crud`
  - active visit context from `visit_crud`
  - card-resolution base data from `card_crud`

This keeps the existing domain logic intact while introducing a repository-level operator projection layer.

## Frontend Integration Notes

Implementation approach:

- Tauri bridge additions were implemented in:
  - `admin-app/src-tauri/src/api_client.rs`
  - `admin-app/src-tauri/src/main.rs`
- The bridge currently returns `serde_json::Value` for the new operator projections.

Reason for this choice:

- it avoids duplicating large evolving operator DTOs in Rust during this increment;
- it keeps the Tauri bridge low-friction while the operator contracts are still growing;
- the typed source of truth remains `backend/schemas.py`.

## Verification Performed

The following checks were run after implementation:

- `python -m pytest backend/tests/test_operator_api.py -q`
- `npm --prefix admin-app run build`
- `npm --prefix admin-app run smoke:cards-guests:lookup`
- `npm --prefix admin-app run smoke:cards-guests:recent-events`
- `cargo check` in `admin-app/src-tauri`

Status:

- backend operator API tests passed
- production web build completed successfully
- targeted cards/guests smoke checks passed
- Tauri/Rust bridge compiled successfully

## New Tests Added

New backend coverage added:

- `backend/tests/test_operator_api.py`

Covered scenarios:

- operator `Today` overview bundle
- operator tap workspace and tap detail
- operator card lookup context

## Known Limits And Deferred Work

This increment establishes the operator projection layer, but it does not complete the full roadmap.

Deferred:

- `GET /api/visits/history` narrative projection redesign beyond the existing route contract
- WebSocket stream and polling fallback
- stale/freshness model visible across all operator routes
- command queue and replay for degraded mode
- full dangerous-action server contracts and reason-code enforcement
- management/reporting layer separation

## Practical Next Step

The next practical implementation track should build on this projection layer instead of bypassing it:

- extend operator projections to sessions/history and deeper incident workflow
- add realtime delivery and reconnect logic
- add degraded-mode visibility and command safety
- move dangerous-action policy enforcement from convention to formal contract
