# Admin App Live Usability Remediation

## 1. Scope

- Admin App live remediation only.
- Related frontend/shared operator models and utilities.
- Backend untouched: existing operator payloads were sufficient for the hotfix.
- Documentation and focused regression tests included.

Out of scope:

- new IA rewrite
- new POS flow
- unrelated feature work

## 2. Confirmed live problems

Functional blockers confirmed in the current live branch state:

- `Guests.svelte` crashed because `formatVolumeRu(...)` was used without importing the formatter.
- `/visits` stayed on `Sessions.svelte` / `SessionHistoryView`, but the screen had no practical visit-start flow, weak explicit continue/open CTAs, and inconsistent cross-route focus behavior.
- `Lost Cards` blocked access with frontend permission `cards_manage`, but that permission key does not exist in the current role model.

Layout and density issues confirmed:

- top shell consumed too much vertical space
- left rail was too wide and too descriptive
- key filter surfaces were too tall on `Визиты`, `Наливы`, `Инциденты`
- first meaningful data was pushed too far below chrome and filters

Language and presentation issues confirmed:

- `Наливы` showed raw internal sync/lifecycle/reason values
- `Кеги и напитки` still showed `Screens`
- shell and route copy still leaked internal wording like `overview`, `lookup`, `guest-facing`

## 3. Functional blockers fixed

### Guests crash

- Fixed direct runtime cause in [admin-app/src/routes/Guests.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Guests.svelte): `formatVolumeRu` is now imported from `lib/formatters.js`.
- Kept the current routed `Guests` screen as canonical and preserved operator actions.
- When opening a visit from guest card, the route now refreshes active visits, guest data, and shell data before redirecting.

### Visit workflow

- Kept `/visits` on [admin-app/src/routes/Sessions.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Sessions.svelte) and remediated the current workspace instead of switching to the unused `Visits.svelte`.
- Added a compact visit launcher to [admin-app/src/components/sessions/SessionHistoryView.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryView.svelte) so an operator can find a guest and either:
  - continue an active visit
  - open a new visit
  - jump to guest context
- Added explicit row CTAs in [admin-app/src/components/sessions/SessionHistoryJournal.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryJournal.svelte): `Продолжить/Открыть`, `Детали`, `Гость`.
- Added contextual shortcuts in [admin-app/src/components/sessions/SessionHistoryDetailDrawer.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryDetailDrawer.svelte): `Открыть гостя`, `Открыть кран`, `Открыть наливы визита`.
- Normalized route focus in [admin-app/src/components/sessions/SessionHistoryView.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryView.svelte) so the workspace now reads `visits.focusVisitId` in addition to existing focus keys.
- Added [admin-app/src/lib/operator/visitWorkspace.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/visitWorkspace.js) with focused regression coverage in [admin-app/src/lib/operator/visitWorkspace.test.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/visitWorkspace.test.js).

### Visit mutation refresh

- Updated [admin-app/src/stores/sessionsStore.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/stores/sessionsStore.js) so close/unlock/reconcile/lost-card actions now refresh:
  - visit journal/detail
  - guest store
  - operator shell shared data

This removes the previous drift between `/visits`, `Смена`, `Гости`, and shell counters after visit mutations.

## 4. Layout and density fixes

### Shell

- Compacted [admin-app/src/components/shell/ShellTopBar.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/shell/ShellTopBar.svelte):
  - smaller padding and gaps
  - shorter search placeholder
  - denser time/operator blocks
  - shorter right-side action labels
- Compacted [admin-app/src/components/shell/ShellStatusPills.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/shell/ShellStatusPills.svelte):
  - smaller pills
  - shorter operational wording
  - less vertical weight
- Reworked [admin-app/src/App.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/App.svelte):
  - removed fixed `calc(100vh - 88px)` workspace height
  - switched workspace to `flex: 1` / `min-height: 0`
  - narrowed rail from `300px` to `248px`
  - enabled independent scrolling for rail and main pane

### Filters

- [admin-app/src/components/sessions/SessionHistoryFiltersPanel.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryFiltersPanel.svelte)
  - primary filter row for common visit search
  - secondary filters behind `Ещё фильтры`
- [admin-app/src/routes/Pours.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Pours.svelte)
  - compact first-row filters
  - advanced checkboxes behind toggle
- [admin-app/src/routes/Incidents.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Incidents.svelte)
  - compact primary queue filters
  - advanced conditions behind toggle

### First-layer visibility

- Tightened spacing on [admin-app/src/routes/Today.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Today.svelte), [admin-app/src/routes/Guests.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Guests.svelte), and [admin-app/src/components/sessions/SessionHistoryView.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryView.svelte).
- Reordered tap card emphasis in [admin-app/src/components/taps/TapCard.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/taps/TapCard.svelte) so guest/visit context now comes before quieter telemetry.

## 5. Operator-language cleanup

- Rewrote visible route/nav copy in [admin-app/src/lib/operator/routeCopy.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/routeCopy.js) to remove `overview`, `lookup`, `guest-facing`, `secondary operational layer`.
- Cleaned shell warning copy in [admin-app/src/components/system/SystemFallbackBanner.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/system/SystemFallbackBanner.svelte).
- Replaced `Screens` with `Экраны` in [admin-app/src/routes/KegsBeverages.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/KegsBeverages.svelte).
- Localized shared quick actions in [admin-app/src/lib/cardsGuests/scenarios/quick_actions.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/cardsGuests/scenarios/quick_actions.js).

### Raw pour codes removed from first layer

- Added [admin-app/src/lib/operator/pourPresentation.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/pourPresentation.js) with tests in [admin-app/src/lib/operator/pourPresentation.test.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/pourPresentation.test.js).
- `Наливы` now show operator-safe Russian labels instead of raw values such as:
  - `accounted`
  - `flow_detected_when_valve_closed_without_active_session`
  - `Card present no`
  - `Start no_card_no_session`
- When a technical code still matters, it is demoted to a quiet secondary detail instead of dominating the first layer.

## 6. Screen-by-screen remediation

### Before / after summary

| Screen | Before | After |
| --- | --- | --- |
| `Гости` | route crashed on render | route builds cleanly, guest actions preserved, density tightened |
| `Визиты` | journal-only feeling, weak open/continue flow | in-place launcher, explicit CTAs, stronger detail shortcuts |
| `Lost Cards` | engineer hit false access restriction | lookup-visible screen with reissue-only mutation gating |
| `Смена` | KPI/header bulk ate the fold | tighter KPI strip and better action-first first view |
| `Наливы` | raw lifecycle/status codes leaked to operators | Russian operator labels with quieter technical detail |
| `Кеги и напитки` | `Screens` and bulky mode switch | denser mode switch, shorter copy, Russian labels |
| `Система` | more technical/scary first layer | calmer operational wording, engineering depth kept secondary |

### Routes and screens touched

- [admin-app/src/routes/Guests.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Guests.svelte)
- [admin-app/src/routes/LostCards.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/LostCards.svelte)
- [admin-app/src/routes/Pours.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Pours.svelte)
- [admin-app/src/routes/Incidents.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Incidents.svelte)
- [admin-app/src/routes/KegsBeverages.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/KegsBeverages.svelte)
- [admin-app/src/routes/System.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/System.svelte)
- [admin-app/src/routes/Today.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/routes/Today.svelte)

### Shared components and utilities touched

- [admin-app/src/App.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/App.svelte)
- [admin-app/src/components/shell/ShellTopBar.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/shell/ShellTopBar.svelte)
- [admin-app/src/components/shell/ShellStatusPills.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/shell/ShellStatusPills.svelte)
- [admin-app/src/components/sessions/SessionHistoryView.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryView.svelte)
- [admin-app/src/components/sessions/SessionHistoryFiltersPanel.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryFiltersPanel.svelte)
- [admin-app/src/components/sessions/SessionHistoryJournal.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryJournal.svelte)
- [admin-app/src/components/sessions/SessionHistoryDetailDrawer.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/sessions/SessionHistoryDetailDrawer.svelte)
- [admin-app/src/components/system/SystemFallbackBanner.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/system/SystemFallbackBanner.svelte)
- [admin-app/src/components/taps/TapCard.svelte](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/components/taps/TapCard.svelte)
- [admin-app/src/stores/sessionsStore.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/stores/sessionsStore.js)
- [admin-app/src/lib/operator/lostCardAccess.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/lostCardAccess.js)
- [admin-app/src/lib/operator/visitWorkspace.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/visitWorkspace.js)
- [admin-app/src/lib/operator/pourPresentation.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/pourPresentation.js)

## 7. Role/access correction

- Root cause: `LostCards.svelte` checked nonexistent frontend permission `cards_manage`.
- Actual frontend/backend policy model already uses `cards_reissue_manage`.
- Added single-source helper in [admin-app/src/lib/operator/lostCardAccess.js](/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/operator/lostCardAccess.js):
  - screen access: `cards_lookup || cards_reissue_manage`
  - restore/reissue mutation access: `cards_reissue_manage`
- This restores engineer access to the screen without making restore/reissue available to lookup-only roles.

## 8. Verification

### Automated verification completed

- `npm --prefix admin-app run build`
- `npm --prefix admin-app run smoke:navigation-ia`
- `npm --prefix admin-app run smoke:cards-guests:lookup`
- `npm --prefix admin-app run smoke:cards-guests:quick-actions`
- `npm --prefix admin-app run test:session-date-filters`
- `node --test admin-app/src/lib/operator/lostCardAccess.test.js`
- `node --test admin-app/src/lib/operator/visitWorkspace.test.js`
- `node --test admin-app/src/lib/operator/pourPresentation.test.js`
- `node --test admin-app/src/lib/operator/copyGuard.test.js`

### Functional confirmation covered by the hotfix

- `Guests` crash path is removed at source: missing formatter import is restored and build succeeds.
- Visit open/continue flow now has direct launcher coverage plus helper tests for candidate resolution and focus target selection.
- Engineer access to `Lost Cards` is covered by focused permission regression tests.

### Manual/live follow-up still recommended

- A full click-through on the running desktop app is still recommended for final sign-off on:
  - visit launcher ergonomics
  - top-shell density on the actual target display
  - first-fold visibility on operator hardware

## 9. Remaining follow-up

- Consider a small visual smoke or component test harness for `Guests` route render safety, because the original crash was a pure runtime symbol miss.
- Consider a dedicated desktop/manual QA pass on the target resolution to fine-tune remaining spacing on `Система` and `Краны`.
- Bundle size warning remains unchanged from the broader branch and is not part of this hotfix scope.

## 10. Final verdict

The Admin App is materially closer to a usable live operator state:

- the known route crash is removed
- visit start/continue is operational again inside the canonical `/visits` workspace
- engineer access to `Lost Cards` matches the intended environment behavior
- shell and filters no longer dominate the first screen as heavily
- raw internal pour codes are no longer leaking into the operator-facing first layer

This is a remediation sprint, not a new IA rewrite, and the fixes stay inside that boundary.
