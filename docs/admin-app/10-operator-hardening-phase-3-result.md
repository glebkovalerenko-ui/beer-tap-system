# Admin App Operator Hardening Phase 3 Result

Date: 2026-03-25

## Purpose

This document records the implemented result of the "Operator Hardening" increment for the existing Admin App.

The goal of this phase was not to introduce a second app or a new IA, but to harden the existing operator-first shell so that it behaves like a live operational product:

- operator-native session projections instead of frontend stitching
- realtime invalidation with degraded-mode fallback
- clearer safety-policy contracts for risky actions
- more explicit operational health and freshness UX

This is an implementation handoff note. It reflects what is now in the repository.

## Scope Implemented

In scope:

- backend operator-first session journal and session detail endpoints
- backend operator system-health projection
- operator stream ticket issuance and WebSocket invalidation channel
- Tauri bridge support for the new operator APIs
- dedicated frontend stores for:
  - sessions projection
  - operator realtime connection state
- degraded/read-only UX for `Today`, `Taps`, `Sessions`, `Cards & Guests`, `Incidents`, and `System`
- freshness chips and route-scoped refetch behavior
- focused backend tests for the new operator APIs

Out of scope:

- offline command queue and replay UI
- fully replacing all legacy mutation endpoints
- management/reporting layer
- full frontend code-splitting/performance cleanup

## Result Summary

The Admin App now behaves as a single operator application with explicit freshness and degraded-state behavior rather than a collection of independent polling screens.

Implemented result:

- `Sessions` no longer builds its model from `activeVisits + sessionHistory + sessionHistoryDetail` on the client. It now consumes operator-first backend projections.
- `Today`, `Taps`, `Incidents`, and `System` can refresh from operator invalidation events instead of relying only on manual refresh or local polling.
- The UI now exposes one shared operator connection state with `websocket`, `short_polling`, and `reduced_polling` modes.
- Dangerous operator actions are blocked in degraded/read-only mode and explained in the UI instead of silently failing later.
- `System` now exposes mode, reason, queue summary, stale-device summary, blocked actions, and actionable next steps.

## Public Contracts Added

New backend endpoints:

- `GET /api/operator/sessions`
- `GET /api/operator/sessions/{visit_id}`
- `GET /api/operator/system`
- `POST /api/operator/stream-ticket`
- `WS /api/operator/stream?ticket=...`

New backend schema types added or extended in `backend/schemas.py`:

- `OperatorSessionJournalFilterParams`
- `OperatorSessionJournalHeader`
- `OperatorSessionJournalItem`
- `OperatorSessionJournalModel`
- `OperatorSessionDetailModel`
- `OperatorSessionActionPolicySet`
- `OperatorSystemQueueSummary`
- `OperatorSystemStaleSummary`
- `OperatorSystemHealthModel`
- `OperatorStreamTicket`
- `OperatorStreamEvent`
- `OperatorConnectionStatus`

Compatibility note:

- incident mutation capabilities now expose the unified policy fields (`allowed`, `confirm_required`, `reason_code_required`, `disabled_reason`) while preserving legacy `enabled/reason` fields for existing consumers.
- `/api/system/status` now also returns legacy-compatible `value: "true" | "false"` alongside the richer operational summary.

## Backend Outcome

Implementation location:

- route layer: `backend/api/operator.py`
- projection assembly: `backend/crud/operator_crud.py`
- stream hub: `backend/operator_stream.py`

Implemented behavior:

- session journal accepts the operator filters already used by the UI:
  - `period_preset`
  - `date_from`
  - `date_to`
  - `tap_id`
  - `status`
  - `card_uid`
  - `completion_source`
  - `incident_only`
  - `unsynced_only`
  - `zero_volume_abort_only`
  - `active_only`
- session list rows now return normalized operator-facing values:
  - normalized `completion_source`
  - `has_zero_volume_abort`
  - `last_operator_action`
  - `pinned_active_sessions`
  - header aggregates
- session detail now returns:
  - narrative timeline
  - display context
  - operator actions
  - safe-action policy set
- operator stream is invalidation-first rather than full-state streaming:
  - `today.updated`
  - `taps.updated`
  - `session.updated`
  - `incident.updated`
  - `system.updated`

## Frontend Outcome

New frontend stores:

- `admin-app/src/stores/sessionsStore.js`
- `admin-app/src/stores/operatorConnectionStore.js`

New shared UI primitive:

- `admin-app/src/components/common/DataFreshnessChip.svelte`

Route-level outcome:

- `Today`
  - freshness chip
  - degraded/read-only banner
  - refetch from operator connection invalidations
- `Taps`
  - freshness chip
  - degraded banner
  - action handlers blocked on degraded mode
  - dangerous tap controls visually disabled in cards/drawer when backend context is stale
- `Sessions`
  - projection-driven list/detail flow
  - shared confirm/reason flows for risky actions
  - freshness and read-only behavior
- `Cards & Guests`
  - route-level degraded warning
  - write flows blocked in read-only mode
  - freshness chip in the header
- `Incidents`
  - now respects global operator degraded/read-only mode
  - freshness chip in the header
- `System`
  - queue backlog
  - stale-device summary
  - blocked actions
  - actionable next steps

## Verification Performed

Verification run after implementation:

- `python -m pytest backend/tests -q`
- `npm --prefix admin-app run build`

Status:

- backend test suite passed: `133 passed, 5 skipped`
- admin-app production build completed successfully

Focused operator coverage added in:

- `backend/tests/test_operator_api.py`

Covered scenarios:

- operator `Today`
- operator `Taps`
- operator `Cards & Guests` lookup
- operator `Sessions` journal filters and detail
- operator `System` health projection
- operator stream ticket issuance and websocket invalidation

## Known Limits

Still deferred after this phase:

- offline replay UI and operator-visible conflict resolution queue
- full replacement of all legacy mutation APIs with operator-specific mutation endpoints
- complete unification of every frontend mutation flow under one shared modal component
- bundle-size optimization for the admin web build

## Practical Next Step

The next practical step should stay on the same trajectory:

- finish migrating the remaining risky mutations to fully unified operator action contracts
- add operator-visible replay/conflict UX for degraded mode
- reduce bundle size and split the operator shell more aggressively
