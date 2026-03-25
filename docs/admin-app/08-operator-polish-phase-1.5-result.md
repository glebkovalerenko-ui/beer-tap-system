# Admin App Operator Polish Phase 1.5 Result

Date: 2026-03-25

## Purpose

This document records the implemented result of the Admin App "Operator Polish" increment inside the current repository.

Phase 1.5 did not introduce a new POS application, new backend APIs, a new routing model, or a new RBAC system. The goal was to reduce operator cognitive load inside the existing shell and make the five core operator routes read like one product.

## Scope Implemented

Phase 1.5 was implemented inside the existing `admin-app` shell and route structure.

Primary operator routes polished in this increment:

- `#/today`
- `#/taps`
- `#/sessions`
- `#/cards-guests`
- `#/incidents`

Supporting operator routes aligned to the same language:

- `#/kegs-beverages`
- `#/tap-screens`
- `#/system`
- `#/settings`
- `#/help`

Out of scope for this increment:

- New backend contracts
- New auth flow
- Route restructuring beyond the existing canonical operator shell
- New polling loops outside `operatorShellOrchestrator`
- Management/reporting layer redesign

## Result Summary

The Admin App now presents a more consistent operator workflow across navigation, route headers, quick actions, list badges, and empty-state language.

The implemented result includes:

- One shared route-copy registry for shell navigation, page headers, and support-nav wording.
- One shared quick-action descriptor model used to standardize action ordering and labels.
- One shared session-badge model so journal rows and active sections use the same operator status language.
- A tap quick-action model that fixes the visible action order to `Open / Stop / Block-Unblock / Screen / Keg / History`.
- Cleaner operator-first copy on Cards & Guests, Incidents, Kegs & Beverages, Tap Screens, System, Settings, and Help.
- Incident action-modal copy rewritten around operator actions instead of backend-oriented language.
- Build warnings removed from `SystemHealthSummary.svelte` and `TapDrawer.svelte`.

## Shared Frontend Contracts Added

New shared frontend-only models added in this increment:

- `admin-app/src/lib/operator/routeCopy.js`
- `admin-app/src/lib/operator/quickActionDescriptors.js`
- `admin-app/src/lib/operator/sessionBadgeModel.js`
- `admin-app/src/lib/operator/tapQuickActions.js`

These additions preserve existing external contracts while standardizing three internal concerns:

- route header copy
- quick action descriptors
- journal/list badge rendering

## Route-by-Route Outcome

### Shell and Navigation

Implemented behavior:

- Primary nav and support nav labels now come from one route-copy registry.
- Page `h1` headers and intro copy now align with shell navigation.
- Support-nav wording stays quiet and operational instead of sounding like a second product area.

Key files:

- `admin-app/src/App.svelte`
- `admin-app/src/lib/operator/routeCopy.js`

### Today

Implemented behavior:

- The route now consumes shared route-header copy.
- The screen remains the operator scan start, but its surrounding shell language is now consistent with the rest of the app.

Key files:

- `admin-app/src/routes/Today.svelte`

### Taps

Implemented behavior:

- Tap-card quick actions now follow one stable order.
- The same action names are used across the card and the drawer.
- Disabled actions now explain why the operator cannot use them in the current state.
- Session-first actions inside the drawer are separated from deeper service actions.
- Unused exported props were removed from the tap drawer.

Key files:

- `admin-app/src/components/taps/TapCard.svelte`
- `admin-app/src/components/taps/TapDrawer.svelte`
- `admin-app/src/lib/operator/tapQuickActions.js`
- `admin-app/src/routes/TapsWorkspace.svelte`

### Sessions

Implemented behavior:

- Session rows now use a shared badge model for `active`, `incident`, `unsynced`, and `zero-volume abort`.
- Detail drawer ordering was refined so sync context and operator actions read more clearly.
- The session narrative remains in the existing journal-plus-drawer flow.

Key files:

- `admin-app/src/components/sessions/SessionHistoryJournal.svelte`
- `admin-app/src/components/sessions/SessionHistoryView.svelte`
- `admin-app/src/components/sessions/SessionHistoryDetailDrawer.svelte`
- `admin-app/src/lib/operator/sessionBadgeModel.js`

### Cards and Guests

Implemented behavior:

- Lookup summary stays focused on operator context only: card state, balance, active visit, last tap, and recent events.
- Quick actions are ordered as `Top up / Block-Unblock / Mark lost or Reissue / Open history / Open active session`.
- Technical wording such as "lookup-summary", "master-data", and "management path" was removed from the operator-facing UI.
- Pending scenario badges are now shown with human-readable operator labels instead of raw scenario ids.

Key files:

- `admin-app/src/routes/CardsGuests.svelte`
- `admin-app/src/components/guests/GuestDetail.svelte`
- `admin-app/src/lib/cardsGuests/scenarios/quick_actions.js`
- `admin-app/src/lib/operator/cardsGuestsModel.js`

### Incidents

Implemented behavior:

- Incident action copy is now phrased in terms of what the operator is doing next.
- Closed incidents remain visible, but are visually quieter than `new` and `in_progress`.
- Detail-panel copy now avoids backend-oriented terms where possible.

Key files:

- `admin-app/src/routes/Incidents.svelte`
- `admin-app/src/components/incidents/IncidentList.svelte`
- `admin-app/src/lib/operator/incidentModel.js`

### Kegs and Beverages / Tap Screens / System

Implemented behavior:

- These routes keep their existing IA, but their page headers and intro copy now use the same operator-first tone as the core workflow.
- Copy was adjusted so `Kegs & Beverages` reads as separate catalog and physical-ops work, `Tap Screens` reads as what the guest sees on the tap, and `System` reads as operational health rather than a developer console.

Key files:

- `admin-app/src/routes/KegsBeverages.svelte`
- `admin-app/src/routes/TapScreens.svelte`
- `admin-app/src/routes/System.svelte`
- `admin-app/src/routes/Settings.svelte`
- `admin-app/src/routes/Help.svelte`

## Verification Performed

The following checks were run after implementation:

- `node --test admin-app/src/lib/operator/todayModel.test.js admin-app/src/lib/operator/incidentModel.test.js admin-app/src/lib/operator/cardsGuestsModel.test.js admin-app/src/lib/operator/tapStateModel.test.js admin-app/src/lib/operator/todayFeedModel.test.js admin-app/src/lib/operator/sessionBadgeModel.test.js admin-app/src/lib/operator/tapQuickActions.test.js admin-app/src/components/sessions/sessionFilters.test.js admin-app/src/components/sessions/sessionNormalize.test.js`
- `npm --prefix admin-app run smoke:navigation-ia`
- `npm --prefix admin-app run build`

Status:

- Targeted operator-model and session tests passed.
- Navigation IA smoke checks passed.
- Production build completed successfully.
- The previous non-blocking warnings in `SystemHealthSummary.svelte` and `TapDrawer.svelte` were removed.

## New Tests Added

New test coverage added in this increment:

- `admin-app/src/lib/operator/sessionBadgeModel.test.js`
- `admin-app/src/lib/operator/tapQuickActions.test.js`

Expanded existing coverage:

- `admin-app/src/lib/operator/cardsGuestsModel.test.js`
- `admin-app/src/lib/operator/incidentModel.test.js`

## Known Limits And Deferred Work

This increment improves consistency and operator clarity, but it does not complete the longer-term management layer.

Deferred or intentionally out of scope:

- Reporting and exports
- Shift-management redesign
- Deep inventory workflows beyond the current `kegs-beverages` route
- Repo-wide `svelte-check` cleanup outside the targeted operator path
- Backend changes for richer operator projections or automation

## Practical Next Step

The next practical track after Phase 1.5 is not another shell rewrite. It is focused product hardening:

- refine empty/loading/error states where backend data is still partial
- extend operator acceptance checks to more role permutations
- tighten action confirmations for the remaining dangerous workflows
- continue management-layer work without polluting the operator-first routes
