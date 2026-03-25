# Admin App Operator Core Phase 1 Result

Date: 2026-03-25

## Purpose

This document records the implemented result of the Admin App "Operator Core" phase inside the current repository. It is a repository-level handoff note, not a new product plan.

The goal of this phase was to turn the existing admin shell into one operator-focused application without introducing a separate POS, separate auth flow, or new backend contracts.

## Scope Implemented

Phase 1 was implemented inside the existing `admin-app` shell and routing model.

In-scope operator routes:

- `#/today`
- `#/taps`
- `#/sessions`
- `#/cards-guests`
- `#/incidents`
- `#/system`

Visible but not deeply redesigned in this phase:

- `#/kegs-beverages`
- `#/tap-screens`

Out of scope for this phase:

- Separate POS application
- New backend endpoints
- RBAC redesign
- Legacy route rework for `Dashboard.svelte` and `Visits.svelte`

## Result Summary

The Admin App now behaves like one operator product instead of a collection of admin screens.

The implemented result includes:

- One operator-first shell with the existing auth and route model preserved.
- A prioritized Today screen that surfaces immediate actions and a normalized event feed.
- Canonical tap operator states extracted into a reusable model.
- Operator-friendly card lookup summary for balance, visit context, last tap, and recent events.
- Incident cards that explicitly show the next operator step.
- Session detail drawer narrative fixed so "what happened" is generated correctly from the completion-source helper.

## Route-by-Route Outcome

### Today

`#/today` is now the default operator scan screen.

Implemented behavior:

- Feed items are normalized into operator language with severity, category, headline, detail, and metric.
- Severity ordering is applied before recency so critical items rise above neutral activity.
- Event dismiss now uses a stable dismiss key and does not depend only on `item_id`.
- Existing hero KPI and action model remain in place, but the feed now matches operator priorities.

Key files:

- `admin-app/src/routes/Today.svelte`
- `admin-app/src/lib/operator/todayFeedModel.js`
- `admin-app/src/components/pours/EventFeed.svelte`

### Taps

`#/taps` remains the main workspace.

Implemented behavior:

- Canonical tap operator states are centralized in a reusable pure model.
- `pouring` no longer uses the critical/red palette as the default visual treatment.
- `no_keg` no longer uses the old purple special case and now maps to warning semantics.
- Tap subsystem pills now support additional operational tones such as `critical`, `error`, `offline`, `degraded`, `unknown`, `info`, and `live`.

Key files:

- `admin-app/src/lib/operator/tapStateModel.js`
- `admin-app/src/stores/tapStore.js`
- `admin-app/src/styles/tokens.css`
- `admin-app/src/components/taps/TapCard.svelte`

### Sessions

`#/sessions` remains the live journal and detail drawer flow.

Implemented behavior:

- Session detail now computes "what happened" using `buildWhatHappened(summary, describeCompletionSource)` in the parent view and passes the resolved text into the drawer.
- This fixes the previous mismatch where the helper was called without the completion-source formatter.

Key files:

- `admin-app/src/components/sessions/SessionHistoryView.svelte`
- `admin-app/src/components/sessions/SessionHistoryDetailDrawer.svelte`

### Cards and Guests

`#/cards-guests` now exposes a faster operator summary directly in the lookup panel.

Implemented behavior:

- Lookup summary items now include balance, last tap, recent-event count, and card status.
- These summary items appear directly in the top lookup result block instead of requiring deeper navigation.
- Route copy was cleaned up to reflect operator context rather than intermediate implementation language.

Key files:

- `admin-app/src/lib/operator/cardsGuestsModel.js`
- `admin-app/src/components/guests/CardLookupPanel.svelte`
- `admin-app/src/routes/CardsGuests.svelte`

### Incidents

`#/incidents` is now closer to an actionable queue than an audit dump.

Implemented behavior:

- Each incident card shows the next operator step from the accountability model.
- Incident cards also expose the first impact/risk statement when available.
- The whole incident card can be selected directly, while inline buttons still stop propagation and preserve their own actions.

Key files:

- `admin-app/src/components/incidents/IncidentList.svelte`

## Public Contract Decisions Preserved

The following project constraints were preserved during implementation:

- Single app, single auth, single route shell.
- Existing role model remains unchanged.
- No new backend endpoints were introduced.
- Operator labels and decisions are derived in frontend view-models from existing payloads.
- Missing or partial backend fields degrade into explicit UI states instead of blocking the screen.

## Verification Performed

The following checks were run after implementation:

- `node --test admin-app/src/lib/operator/todayModel.test.js admin-app/src/lib/operator/incidentModel.test.js admin-app/src/lib/operator/cardsGuestsModel.test.js admin-app/src/lib/operator/tapStateModel.test.js admin-app/src/lib/operator/todayFeedModel.test.js admin-app/src/components/sessions/sessionFilters.test.js admin-app/src/components/sessions/sessionNormalize.test.js`
- `npm --prefix admin-app run smoke:navigation-ia`
- `npm --prefix admin-app run build`

Build status:

- Production build completed successfully.
- Navigation IA smoke checks passed.
- Targeted operator-model and session tests passed.

## New Tests Added

New test coverage added in this phase:

- `admin-app/src/lib/operator/tapStateModel.test.js`
- `admin-app/src/lib/operator/todayFeedModel.test.js`

Expanded existing coverage:

- `admin-app/src/lib/operator/cardsGuestsModel.test.js`

## Known Limits And Deferred Work

This phase intentionally does not solve every admin-app issue.

Deferred or intentionally out of scope:

- Repo-wide `svelte-check` baseline cleanup
- Deep redesign of `kegs-beverages` and `tap-screens`
- Management/reporting layer beyond operator core
- Legacy route cleanup outside the active operator shell

At the time of implementation, `vite build` still reports older warnings in unrelated files:

- `admin-app/src/components/system/SystemHealthSummary.svelte`
- `admin-app/src/components/taps/TapDrawer.svelte`

These warnings were not introduced by the Operator Core implementation and remain a separate cleanup track.

## Recommended Next Step

If the team continues this track, the next practical increment is "Operator Polish":

- tighten copy consistency across the shell
- reduce click count in repeated actions
- improve empty/error/loading states on all operator routes
- clean the remaining non-blocking warnings in adjacent operator components

Status update:

- This next step was implemented on 2026-03-25 and is documented in `docs/admin-app/08-operator-polish-phase-1.5-result.md`.
