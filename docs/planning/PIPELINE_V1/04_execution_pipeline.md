# Execution Pipeline (Milestone-Based)

Principles:
- Incremental, demonstrable outcomes.
- Additive changes first; avoid breaking current demo flows.
- Explicit rollback at each step.

---

## Milestone 0 — Baseline contract freeze and observability hooks

**Goal**
- Freeze current API/controller/admin behavior baseline and introduce compatibility guardrails before domain expansion.

**Exact scope**
- Baseline API contract snapshot and scenario baseline tests.
- Add naming/taxonomy decision docs for new operational entities.

**Files/areas likely touched**
- `docs/planning/PIPELINE_V1/*`
- `docs/API_REFERENCE.md` and/or `docs/INTERFACE_CONTRACT.md` (delta notes)
- test files under `backend/tests/` and controller test harness docs.

**Required backend changes**
- None mandatory (documentation + test scaffolding allowed).

**Required controller changes**
- None.

**Required admin UI changes**
- None.

**Testing/verification checklist**
- Execute baseline endpoint smoke checks.
- Confirm current pour sync still idempotent.

**Acceptance criteria**
- Signed baseline checklist with current behaviors and known deviations from model.

**Risks + rollback**
- Risk: stale baseline if skipped.
- Rollback: N/A (documentation-only).

---

## Milestone 1 — Domain model alignment (data layer foundation)

**Goal**
- Add minimum operational entities/columns required by spec while preserving existing flows.

**Exact scope**
- Add additive backend schema for:
  - `Visit` (+ `active_tap_id`, status timestamps/reason),
  - `LostCard`,
  - `Alert`,
  - `Shift`, `ShiftMember`,
  - `Location` (single default location bootstrap),
  - Pour `sync_status`,
  - Tap status extension to include `processing_sync` and `out_of_keg` (or mapping strategy).

**Files/areas likely touched**
- `backend/models.py`, `backend/schemas.py`, `backend/crud/*`, `backend/api/*`
- `backend/alembic/*` (introduce first migration versions)
- Optional: `docs/sqlite_schema.sql`, `docs/postgres_schema.sql` sync updates.

**Required backend changes**
- Schema additions + migration scripts.
- Backward-compatible defaults so current endpoints keep functioning.

**Required controller changes**
- None in this milestone.

**Required admin UI changes**
- None required yet (optional hidden telemetry display).

**Testing/verification checklist**
- Migration up/down validation in clean DB.
- Existing API regression (guests/taps/kegs/pours) unaffected.

**Acceptance criteria**
- New tables/columns exist and are queryable.
- No regression in current demo path.

**Risks + rollback**
- Risk: migration drift due to no prior alembic versions.
- Rollback: reversible migration scripts; backup/restore playbook.

---

## Milestone 2 — Visit lifecycle (open/close + invariants)

**Goal**
- Implement Visit as the canonical operational session.

**Exact scope**
- Backend endpoints/service for open/close visit.
- Invariants:
  - one active visit per guest,
  - card bound to active visit,
  - close visit deactivates card.
- Audit events for open/close and rejected opens.

**Files/areas likely touched**
- `backend/api/guests.py` (or new `backend/api/visits.py` — **Proposed**)
- `backend/crud/guest_crud.py`, new visit CRUD/service module (**Proposed**)
- `backend/schemas.py`, `backend/models.py`
- admin route/store additions (**Proposed**): `admin-app/src/stores/visitStore.js`, guest detail actions.

**Required backend changes**
- New Visit endpoints and enforcement service.

**Required controller changes**
- None yet (authorization still legacy until Milestone 3).

**Required admin UI changes**
- Add explicit Visit open/close operations in guest workflow (**Proposed** UI elements).

**Testing/verification checklist**
- Open visit happy path.
- Duplicate active visit rejected.
- Close visit deactivates card.

**Acceptance criteria**
- Each active card in system maps to one active visit.
- Visit closure reflects immediately in authorization checks.

**Risks + rollback**
- Risk: dual mode confusion (legacy card-active logic vs visit logic).
- Rollback: feature flag to keep legacy auth path while debugging.

---

## Milestone 3 — PourSession sync lifecycle + `processing_sync`

**Goal**
- Align offline sync semantics with explicit server-state representation.

**Exact scope**
- Extend pour ingestion path to set/transition `sync_status`.
- Introduce `processing_sync` tap behavior for reconciliation windows.
- Ensure reconciliation clears visit `active_tap_id` when complete.

**Files/areas likely touched**
- `backend/main.py` sync endpoint
- `backend/crud/pour_crud.py`, tap/visit service modules
- `backend/models.py` + schemas
- `rpi-controller/sync_manager.py`, `rpi-controller/database.py` (state mapping adjustments)
- Admin visibility in dashboard/store (read-only status indicators).

**Required backend changes**
- New sync-state transition logic + APIs to inspect pending sync.

**Required controller changes**
- Interpret and respect tap `processing_sync` / no-new-card condition.
- Propagate sync result handling with deterministic retry policy.

**Required admin UI changes**
- Show pending sync count and tap sync state.

**Testing/verification checklist**
- Simulated disconnection mid-pour then recovery.
- pending_sync -> synced transition and lock release.

**Acceptance criteria**
- No new authorization on taps marked `processing_sync`.
- Completed reconciliation clears pending queue and tap state.

**Risks + rollback**
- Risk: deadlocks where tap never exits `processing_sync`.
- Rollback: admin recovery action to force safe unlock with audit trail.

---

## Milestone 4 — Active tap lock (`active_tap_id`) & simultaneous-use prevention

**Goal**
- Enforce one-card/one-active-tap runtime constraint across controllers.

**Exact scope**
- Pre-pour authorization endpoint/service returns allow/deny with reason.
- Deny path includes "card already in use on Tap X" semantics.
- Event/audit logging for denied attempts.

**Files/areas likely touched**
- Backend new authorization service/API (**Proposed** under `/api/controllers/*` namespace)
- `rpi-controller/flow_manager.py` / `sync_manager.py` call sequence update
- Admin monitoring view for active locks (**Proposed**)

**Required backend changes**
- Authorize/start-pour and finalize-pour orchestration hooks.

**Required controller changes**
- Shift from static "card exists" authorization to server decision contract.

**Required admin UI changes**
- Display current active tap usage/locks.

**Testing/verification checklist**
- Two controllers attempt same card concurrently; second denied.
- Lock released after completion/sync recovery.

**Acceptance criteria**
- Zero successful simultaneous pours for same active visit.

**Risks + rollback**
- Risk: partial failures leave stale locks.
- Rollback: lock timeout + audited manual unlock endpoint.

---

## Milestone 5 — LostCard registry and enforcement

**Goal**
- Operationalize lost-card handling as separate domain record.

**Exact scope**
- LostCard CRUD/reporting.
- Authorization-time check against LostCard registry.
- Critical alert on lost-card usage attempt.

**Files/areas likely touched**
- Backend: new lost card model/service/API, alert integration.
- Admin app: lost-card reporting action in guest context (**Proposed**), registry list panel.
- Controller: consume deny reason and display/act accordingly.

**Required backend changes**
- LostCard entity + policy checks in authorization path.

**Required controller changes**
- Block immediately on deny reason lost-card.

**Required admin UI changes**
- Report lost card and view active lost list.

**Testing/verification checklist**
- Mark card lost then attempt pour.
- Verify deny + critical alert generated.

**Acceptance criteria**
- Any lost UID usage attempt creates auditable critical alert and denied pour.

**Risks + rollback**
- Risk: false positives from UID normalization mismatch.
- Rollback: temporary allowlist override with high-severity audit.

---

## Milestone 6 — Keg lifecycle alignment + FIFO suggestion

**Goal**
- Align keg operational states and replacement guidance with spec.

**Exact scope**
- Keg schema enrichment (`received_at`, `connected_at`, `disconnected_at`, `remaining_volume_l`, status map).
- FIFO query: next keg suggestion by same beer type and oldest warehouse receipt.
- Tap transition to `out_of_keg` and back to active on confirmed replacement.

**Files/areas likely touched**
- Backend models/schemas/keg CRUD/tap CRUD.
- Admin assign keg modal and tap card status displays.

**Required backend changes**
- FIFO suggestion service/API and state transitions.

**Required controller changes**
- None mandatory if tap status consumed from backend.

**Required admin UI changes**
- Show suggested keg in assignment flow.

**Testing/verification checklist**
- Multiple warehouse kegs for same beer type; verify oldest selected.
- Empty keg transition and replacement flow.

**Acceptance criteria**
- FIFO suggestion deterministic and auditable.

**Risks + rollback**
- Risk: historical data lacks received timestamps.
- Rollback: fallback rule uses created_at until data backfilled.

---

## Milestone 7 — Alerts severity matrix + acknowledge/resolve

**Goal**
- Introduce operational alerting backbone.

**Exact scope**
- Alert entity/API:
  - severities info/warning/critical,
  - acknowledge and resolve actions with actor/comment metadata.
- Initial rules:
  - lost-card use => critical,
  - keg thresholds,
  - sync mismatch => warning/critical by threshold.

**Files/areas likely touched**
- Backend alert model/API/rule evaluator.
- Admin app alert list/filter/action components (**Proposed route or dashboard panel**).

**Required backend changes**
- Alert lifecycle service + rule emitters.

**Required controller changes**
- None directly; may consume alert-driven state via authorization responses.

**Required admin UI changes**
- Acknowledge/resolve workflows with comments.

**Testing/verification checklist**
- Generate each severity level and execute ack/resolve transitions.

**Acceptance criteria**
- All critical operational exceptions surface as alerts within bounded latency.

**Risks + rollback**
- Risk: noisy alerts overwhelm staff.
- Rollback: tune threshold configs and temporary suppression rules.

---

## Milestone 8 — Shift backend model + closing wizard

**Goal**
- Replace local-only shift behavior with authoritative backend lifecycle and closure gating.

**Exact scope**
- Shift + ShiftMember API.
- Closing wizard checks:
  - no active visits,
  - no pending sync,
  - unresolved alerts shown,
  - equipment inspection confirmation,
  - shift summary and final close.
- Report generation with required minimum metrics.

**Files/areas likely touched**
- Backend shift models/services/report query logic.
- Admin dashboard/shift store/wizard UI components.

**Required backend changes**
- Shift lifecycle + close precheck endpoint.

**Required controller changes**
- None mandatory.

**Required admin UI changes**
- Migrate `shiftStore` from localStorage to API-driven state.

**Testing/verification checklist**
- Attempt close with active visit -> blocked.
- Attempt close with pending sync -> blocked.
- Critical unresolved alerts visible and acknowledge path works.

**Acceptance criteria**
- Shift close impossible when hard blockers exist.
- Shift report contains required fields.

**Risks + rollback**
- Risk: operational disruption during migration from local shift handling.
- Rollback: dual-write period (UI local + backend) before switching source of truth.

---

## Milestone 9 — POSAdapter boundary definition (MVP stub)

**Goal**
- Introduce explicit integration boundary without deep POS coupling.

**Exact scope**
- Define and implement internal interface for:
  - `notify_topup`, `notify_refund`, `notify_pour`.
- MVP adapter mode: noop/log/manual queue (semi-manual sync per spec).
- Event emission points integrated into topup/refund/pour completion.

**Files/areas likely touched**
- Backend service layer (new adapter interface module).
- Docs: `docs/INTERFACE_CONTRACT.md` + ops docs.

**Required backend changes**
- Adapter abstraction + configuration toggle.

**Required controller changes**
- None.

**Required admin UI changes**
- Optional monitoring of outbound adapter queue/events (**Proposed**).

**Testing/verification checklist**
- Verify topup/pour emits adapter calls in stub mode and failures are non-blocking (or policy-defined).

**Acceptance criteria**
- Core domain operates with adapter disabled/enabled without logic forks.

**Risks + rollback**
- Risk: coupling adapter failures to transactional core.
- Rollback: isolate adapter to outbox/event queue and fail-open for MVP.

---

## Recommended sequence rationale
1. Foundation schema first (M1), then core operational invariant (M2-M4).
2. Risk-heavy safety controls next (M5-M7).
3. Shift discipline once blockers exist (M8).
4. POS boundary last in MVP since integration is intentionally shallow (M9).
