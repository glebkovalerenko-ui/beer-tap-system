# RUS Localization Phase 1 Implementation

## 1. Scope of phase 1

Phase 1 was limited to the display layer:

- operator-facing UI strings in `admin-app`
- operator-facing date/time, money, and volume formatting
- controller terminal progress and operational messages
- operator-facing report labels and visible status mappings
- developer/operator documentation for this phase

The phase explicitly did not change backend/API contracts, database schema, migrations, DTO naming, or business logic.

## 2. What was done

Implemented a shared formatting layer in `admin-app/src/lib/formatters.js` and applied it across dashboard, reports, pours, guest screens, visits, taps, kegs, modals, shell widgets, and the app entry HTML.

Implemented Russian operator-facing message cleanup in `admin-app`:

- removed visible `$`, raw `amount_cents`, and `total_amount_cents` output from reports and lists
- replaced mixed labels such as `Beer Tap POS`, `POS Workspace`, `Demo mode`, `Online/Offline`, `Guest ID`, `processing_sync`, `lock_set_at`, and `reported_at`
- translated manual reconcile placeholders and visible visit/lost-card labels
- normalized common backend error text in `admin-app/src/lib/errorUtils.js`

Implemented controller display-layer localization in `rpi-controller`:

- added `display_formatters.py` for operator-facing money and volume output
- localized live terminal progress lines and session completion messages
- localized key flow-manager and sync-manager messages used during operation
- updated controller tests to assert Russian display output

## 3. What was intentionally not touched

- internal money fields such as `*_cents`, `price_cents`, `balance_cents`, `amount_cents`
- internal volume fields such as `*_ml`
- backend schemas, API payload shape, Tauri Rust DTO naming, and controller sync payloads
- database schema and migrations
- POS / r_keeper integration and broader architecture work
- domain-model renames or refactors beyond display formatting and operator text

## 4. Added formatters

`admin-app/src/lib/formatters.js`

- `formatMinorUnitsRub(minorUnits)` -> `123,45 ₽`
- `formatRubAmount(value)` -> helper for existing decimal-ruble strings/numbers in current UI payloads
- `formatVolumeRu(volumeMl)` -> `50 мл`, `430 мл`, `1,2 л`
- `formatVolumeRangeRu(currentMl, totalMl)` -> range display for kegs
- `formatDateRu(value)` -> `10.03.2026`
- `formatTimeRu(value)` -> `14:25`
- `formatDateTimeRu(value)` -> `10.03.2026, 14:25`
- `formatDurationRu(durationMs)` -> `12 с`, `1 мин 05 с`
- display label mappers for taps, visits, cards, kegs, and shift-report metrics

`rpi-controller/display_formatters.py`

- `format_money_minor_units(minor_units)` -> `123,45 ₽`
- `format_volume(volume_ml)` -> `50 мл`, `1,2 л`

## 5. Localized screen and message groups

- app shell, title, demo mode controls, status pills, server settings, and activity trail
- dashboard shift panel and Z-report list
- shift report modal and investor metrics
- live pour feed
- guest list, guest detail, top-up modal
- visit list, visit detail, manual reconcile, and card lookup flows
- lost-card search and list view
- tap cards, keg list, keg form, and assign-keg modal
- controller terminal progress, sync reminders, deny messages, startup probe, and shutdown output

## 6. What remains for Phase 2

- glossary alignment for wider documentation and technical/operator terminology boundaries
- deeper backend-originated error translation if more raw English messages still surface at runtime
- broader audit of developer docs and historical runbooks where mixed terminology is still acceptable today but may need cleanup later
- any decision about renaming internal `*_cents` / `*_ml` fields, which remains out of scope and high risk

## 7. Manual verification

1. Open the admin app and confirm the shell title, demo controls, network status, and server settings are in Russian.
2. Check dashboard, pour feed, guest screens, visits, lost cards, taps, kegs, and reports for:
   - money shown in `₽`
   - volume shown in `мл/л`
   - date/time shown in `ru-RU` style
   - no raw `$`, `USD`, `cents`, `processing_sync`, `lock_set_at`, or `reported_at` in operator-facing UI
3. Run a controller session or controller tests and confirm terminal progress uses Russian text plus `₽` and `мл/л`.
4. Run the required verification commands:
   - `python scripts/encoding_guard.py --all`
   - `cd admin-app && npm run build`
   - `cd admin-app && npm run smoke:login-settings`
   - `cd admin-app/src-tauri && cargo check`
5. If any operator-facing backend error still appears in English, capture the exact text for Phase 2 display mapping expansion.
