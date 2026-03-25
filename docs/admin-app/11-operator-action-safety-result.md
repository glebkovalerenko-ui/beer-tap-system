# Admin App Operator Action Safety Result

Date: 2026-03-25

## Purpose

This document records the implemented result of the "Operator Action Safety" increment for the existing Admin App.

The purpose of this increment was to finish the next practical hardening step after operator projections and degraded-mode support:

- unify risky operator actions behind one shared modal model
- stop using ad-hoc confirms and `window.prompt`
- show blocked/disabled reasons consistently across operator routes
- preserve existing IA, auth, routing, and mutation endpoints
- extend contracts only additively where safety context was missing

This is an implementation handoff note. It reflects what is now in the repository.

## Scope Implemented

In scope:

- shared operator action descriptor/policy/modal layer
- `Taps` migration to policy-driven status actions
- `Sessions` migration to shared confirm/reason flow
- `Cards & Guests` migration away from local action heuristics for risky actions
- `Incidents` migration from route-local modal to shared operator action flow
- read-only blocked-action normalization for `System`
- additive backend extensions for:
  - tap status mutation audit context
  - card lookup action policies

Out of scope:

- new routes or a separate POS app
- RBAC redesign
- second-person approval workflow
- replay/conflict UI
- management/reporting layer
- legacy `Dashboard` / `Visits` route cleanup

## Result Summary

The Admin App now uses one shared operator safety pattern for dangerous or state-changing actions across the core operator shell.

Implemented result:

- operator actions are now defined through shared descriptors rather than route-local modal logic
- policy normalization now maps backend capability contracts into one frontend shape:
  - `allowed`
  - `confirm_required`
  - `reason_code_required`
  - `second_approval_required`
  - `disabled_reason`
- `Sessions`, `Taps`, `Cards & Guests`, and `Incidents` all use the same operator action modal
- blocked/read-only reasons are now surfaced consistently instead of being silently inferred or hidden behind different UI patterns
- tap status changes now support explicit audit context with optional `reason_code` and `comment`
- card lookup now returns additive `action_policies` while preserving legacy `allowed_quick_actions`

## Public Contracts Added Or Extended

Backend schema additions and extensions in `backend/schemas.py`:

- `TapUpdate`
  - optional `reason_code`
  - optional `comment`
- `CardGuestActionPolicySet`
- `CardGuestContextModel.action_policies`

Compatibility preserved:

- existing tap mutation payloads remain valid without `reason_code` / `comment`
- existing card lookup consumers can still use legacy `allowed_quick_actions`
- tap action policy wire shape is unchanged:
  - `stop`
  - `block`
  - `screen`
  - `history`
  - `keg`

## Backend Outcome

Implementation location:

- `backend/api/taps.py`
- `backend/crud/tap_crud.py`
- `backend/crud/operator_crud.py`
- `backend/security.py`

Implemented behavior:

- tap status updates now accept optional safety metadata without breaking existing clients
- tap audit logging now records:
  - previous status
  - next status
  - tap identity context
  - optional `reason_code`
  - optional `comment`
- card lookup now returns backend-driven action policies for:
  - `top_up`
  - `toggle_block`
  - `mark_lost`
  - `restore_lost`
  - `reissue`
  - `open_history`
  - `open_visit`

## Frontend Outcome

Shared operator safety layer added:

- `admin-app/src/lib/operator/actionReasonCodes.js`
- `admin-app/src/lib/operator/actionPolicyAdapter.js`
- `admin-app/src/lib/operator/actionDescriptors.js`
- `admin-app/src/lib/operator/actionDialogModel.js`
- `admin-app/src/stores/operatorActionStore.js`
- `admin-app/src/components/feedback/OperatorActionModal.svelte`

Route-level outcome:

- `Taps`
  - `stop` now uses backend `safe_actions.stop` and shared reason-code flow
  - lock/unlock actions now use the shared descriptor/policy flow
  - maintenance actions now use the same modal model instead of route-local confirms
  - card and drawer surfaces now respect the same disabled/read-only reasons
- `Sessions`
  - route-local prompts were removed
  - `close`, `force_unlock`, `reconcile`, and `mark_lost_card` now use the shared modal
- `Cards & Guests`
  - risky actions now use backend `action_policies` instead of local gating heuristics
  - `mark lost`, `restore lost`, and guest block/unblock now use the shared modal
  - quick-action ordering remains unchanged
- `Incidents`
  - claim/note/escalate/close semantics stay unchanged
  - action collection now uses the shared descriptor/policy pattern instead of a route-local modal
- `System`
  - remains read-only
  - blocked actions are now rendered through the same policy adapter semantics used elsewhere

## Verification Performed

Verification run after implementation:

- `python -m pytest backend/tests/test_operator_api.py -q`
- `node --test admin-app/src/**/*.test.js`
- `npm --prefix admin-app run build`

Status:

- focused backend operator API coverage passed: `9 passed`
- admin-app test suite passed: `37 passed`
- admin-app production build completed successfully

New or expanded frontend coverage includes:

- `admin-app/src/lib/operator/actionPolicyAdapter.test.js`
- `admin-app/src/lib/operator/actionDialogModel.test.js`
- `admin-app/src/lib/operator/actionDescriptors.test.js`
- `admin-app/src/lib/operator/tapQuickActions.test.js`
- `admin-app/src/lib/operator/cardsGuestsModel.test.js`

## Known Limits

Still deferred after this increment:

- second-person approval execution flow
- operator-visible replay/conflict UI
- migration of every remaining legacy mutation screen to the shared operator action layer
- bundle-size optimization for the admin build

## Practical Next Step

The next practical step should stay on the same track:

- finish migrating remaining legacy mutation flows outside the core operator shell
- add replay/conflict UX for degraded or delayed backend states
- split the admin build more aggressively to reduce the large operator bundle warning
