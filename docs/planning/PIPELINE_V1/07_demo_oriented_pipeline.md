# Pilot-Ready Demo Pipeline — OPERATIONAL_MODEL_V1 Alignment

## 1) Executive Summary

## What this pipeline ensures for pilot safety
This roadmap keeps demo velocity while making the system safe for a real bar pilot:
- **Visit is the invariant root** (single active visit per guest).
- **Active tap lock** prevents simultaneous card use.
- **Offline flow is deterministic** with explicit `sync_status` and bounded recovery behavior.
- **Shift lifecycle is backend-authoritative** (not localStorage-authoritative).
- **Schema evolution is migration-controlled** (Alembic baseline + additive-first).
- **POS integration is isolated behind a stub boundary** so core domain is stable while external integrations mature.

It preserves core architecture:
- Controller = source of truth for measured volume.
- Backend = source of truth for operational state.

## What this pipeline intentionally postpones
Out of scope (by design):
- Full alert lifecycle engine.
- Complex reconciliation/dispute engine.
- Enterprise RBAC / advanced role hierarchy.
- Multi-location runtime behavior.
- Deep POS transactional coupling/fiscalization logic.
- Production HA / redundancy architecture.

---

## 2) Refined Milestones (Pilot-Ready)

## M1 — Migration baseline + additive schema guardrails
**Goal**
- Introduce migration discipline before new pilot-critical behavior.

**Scope**
- Establish Alembic baseline for current live schema.
- Define additive-first migration policy and rollback playbook.
- Add minimal future columns/tables as nullable/default-safe where needed.

**Schema impact**
- No destructive changes.
- Baseline revision + optional additive placeholders only.

**Migration strategy impact**
- This milestone is where migration discipline begins.
- Future milestones must ship as forward-only additive revisions with tested downgrades for pilot rollback.

**Backend changes**
- `backend/alembic/` revisions, migration docs updates.

**Controller changes**
- None.

**Admin UI changes**
- None.

**Operational risk level**
- **Med** (baseline correctness risk).

**Demo value gained**
- Pilot credibility: controlled evolution, no ad-hoc DB drift.

---

## M2 — Visit model as invariant root
**Goal**
- Make Visit the canonical session entity.

**Scope**
- Open/close visit endpoints and service.
- Enforce one active visit per guest.
- Card deactivates on visit close.

**Schema impact**
- Add `visits` table (+ status/timestamps/reason, `active_tap_id` nullable).

**Migration strategy impact**
- Additive table introduction; no backfill required to keep demo data intact.

**Backend changes**
- Visit model/schema/CRUD/API and invariant checks.

**Controller changes**
- None yet (authorization integration comes next).

**Admin UI changes**
- Minimal visit controls in guest flow (Open Visit / Close Visit + current state).

**Operational risk level**
- **Med**.

**Demo value gained**
- Clear operational session discipline in investor/pilot demo.

---

## M3 — Active tap lock semantics (anti-simultaneous usage)
**Goal**
- Enforce anti-cloning behavior in real-time tap authorization.

**Scope**
- Backend authorization decision path returns allow/deny + reason.
- Set `active_tap_id` on start authorization.
- Deny if already locked to another tap.

**Schema impact**
- Uses `visits.active_tap_id` from M2.

**Migration strategy impact**
- No destructive migration; behavior gated by feature flag.

**Backend changes**
- Lightweight controller-facing authorization endpoint/service.
- Audit/event entry for denied simultaneous attempts.

**Controller changes**
- Switch from "card exists" lookup to backend authorization call.

**Admin UI changes**
- Read-only lock indicator (e.g., "in use on Tap X").

**Operational risk level**
- **High** (lock consistency risk).

**Demo value gained**
- Strong security story (card-sharing prevention).

---

## M4 — Minimal deterministic offline sync
**Goal**
- Keep pours resilient offline without building a complex reconciliation platform.

**Scope**
- Explicit `sync_status` on pour sessions (`pending_sync` / `synced`).
- Tap status includes `processing_sync` during unresolved sync window.
- No new authorization while tap is `processing_sync`.
- On sync success: mark synced, clear lock, return tap to active.

**Schema impact**
- Add `pours.sync_status` (default safe).
- Extend tap status domain for `processing_sync`.

**Migration strategy impact**
- Additive columns/state extension with defaults to preserve old data behavior.

**Backend changes**
- Update sync ingestion and state transitions.
- Deterministic ordering for lock release after sync success.

**Controller changes**
- Respect `processing_sync` deny path.
- Keep current local queue/retry loop; no controller re-architecture.

**Admin UI changes**
- Pending sync counter + tap state pill.

**Operational risk level**
- **High** (**highest operational risk milestone**).

**Demo value gained**
- Credible offline resilience in real pilot conditions.

---

## M5 — Simplified LostCard registry + enforcement
**Goal**
- Provide practical abuse prevention with minimal scope.

**Scope**
- LostCard registry (report + list).
- Authorization hard-deny when UID is in LostCard.
- Minimal audit/event entry (not full alert lifecycle).

**Schema impact**
- Add `lost_cards` table linked to guest/visit where available.

**Migration strategy impact**
- Additive table only.

**Backend changes**
- LostCard CRUD + check in authorization service.

**Controller changes**
- Surface deny reason and keep valve closed.

**Admin UI changes**
- "Report Lost Card" action + simple registry list.

**Operational risk level**
- **Med**.

**Demo value gained**
- Operational security control visible to staff/investors.

---

## M6 — Backend-backed Shift lifecycle (minimal pilot discipline)
**Goal**
- Move shift authority from frontend local state to backend state.

**Scope**
- Shift open/close API.
- Minimal close blockers:
  1) no active visits,
  2) no pending_sync pours.
- Simple precheck response for close action.

**Schema impact**
- Add `shifts` table (and minimal association only if needed for current UI).

**Migration strategy impact**
- Additive table introduction.

**Backend changes**
- Shift model/service/API + close precheck endpoint.

**Controller changes**
- None.

**Admin UI changes**
- `shiftStore` becomes backend-backed authority.
- Minimal close-check modal (not full wizard).

**Operational risk level**
- **Med**.

**Demo value gained**
- Pilot-safe operational discipline with measurable close control.

---

## M7 — FIFO keg suggestion + POSAdapter boundary (stub mode)
**Goal**
- Complete pilot demo narrative: inventory guidance + POS-ready architecture.

**Scope**
- FIFO suggestion endpoint (same beer type, oldest warehouse candidate).
- Recommendation-only UX (operator confirms manually).
- POSAdapter interface boundary with stub/log implementation only.

**Schema impact**
- Minimal keg metadata additions only if required for FIFO ordering.

**Migration strategy impact**
- Additive metadata columns with safe defaults.

**Backend changes**
- FIFO query logic.
- POSAdapter interface module + stub adapter wired to top-up/pour/refund events.

**Controller changes**
- None.

**Admin UI changes**
- Show suggested keg in assignment flow.
- Optional status marker for POS stub event emission.

**Operational risk level**
- **Low-Med**.

**Demo value gained**
- “POS-ready, not POS-dependent” architecture message.

---

## Safe rollout order and feature flags

## Safe rollout order
1. M1 (migration baseline)
2. M2 (Visit root)
3. M3 (active lock)
4. M4 (offline sync semantics)
5. M5 (LostCard)
6. M6 (backend Shift)
7. M7 (FIFO + POSAdapter stub)

## Recommended feature flags
- `FF_VISIT_ENFORCEMENT` (M2)
- `FF_ACTIVE_TAP_LOCK` (M3)
- `FF_SYNC_STATUS_ENFORCEMENT` (M4)
- `FF_LOST_CARD_ENFORCEMENT` (M5)
- `FF_BACKEND_SHIFT_AUTHORITY` (M6)
- `FF_POS_ADAPTER_STUB` (M7)

Use flags for staged rollout + quick rollback without schema rollback.

---

## 3) Migration Strategy

## 3.1 Alembic baseline introduction (safe path)
1. Snapshot current DB schema in pilot/staging.
2. Create Alembic baseline revision representing current state.
3. Validate baseline against fresh DB and clone of current data.
4. Freeze direct schema edits; all changes via Alembic revisions only.

## 3.2 Existing schema handling
- Do not mutate or drop current tables during baseline.
- Introduce new entities/columns additively.
- Keep legacy reads/writes operational until feature flag flips.

## 3.3 Additive migration pattern (mandatory)
- Add table/column nullable or with defaults.
- Deploy code that can read both old/new paths.
- Flip feature flag when validated.
- Backfill only if needed and in reversible small batches.
- Enforce stricter constraints only after backfill verification.

## 3.4 Rollback strategy
- **Behavior rollback first**: disable feature flag.
- **Schema rollback second**: only if necessary, via tested Alembic downgrade.
- Keep DB backup before each milestone rollout.
- No destructive migrations in pilot phase.

---

## 4) Pilot Safety Considerations

## Data integrity guarantees
- One active visit per guest enforced server-side.
- Active tap lock state transition is backend-authoritative.
- Idempotent pour sync remains keyed by `client_tx_id`.

## Offline behavior guardrails
- Active pour can complete locally on controller.
- New authorization blocked when tap is `processing_sync`.
- Sync completion is the deterministic unlock trigger.

## Lock recovery strategy
- Auto-recovery on successful sync path.
- If lock remains stale beyond threshold, allow audited manual unlock endpoint/action.

## Manual escape hatches (minimal)
- Audited admin action: force-clear stale `active_tap_id`.
- Audited admin action: mark tap back to `active` after verified reconciliation.

(These are operational safety valves, not replacement for normal flow.)

---

## 5) Architectural Integrity Check

## No future rewrite trap
- Additive schema and feature-flagged behavior keep extension paths open.
- POSAdapter introduced as interface seam, not hard dependency.

## No contradictory state models
- Visit owns session invariants.
- Tap lock and sync states are explicit and deterministic.
- Controller and backend source-of-truth boundaries stay unchanged.

## No hidden enterprise complexity
- No full alert engine, no enterprise RBAC, no distributed multi-node logic, no deep POS coupling.

## No breaking of OPERATIONAL_MODEL_V1 invariants
- Preserves required invariants for Visit lifecycle, anti-simultaneous usage, offline sync handling, LostCard enforcement, and shift closure discipline within demo/pilot scope.
