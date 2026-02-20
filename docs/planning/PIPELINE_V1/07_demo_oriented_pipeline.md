# Demo-Oriented Pipeline — OPERATIONAL_MODEL_V1 Alignment

## 1) Executive Summary

## What this pipeline achieves
This demo-oriented pipeline delivers **architecturally credible operations** with minimum implementation surface:
- Visit model with **single active visit** invariant.
- Active tap lock (`active_tap_id`) to block simultaneous card usage.
- Minimal offline sync model with explicit `sync_status` (`pending_sync` / `synced`).
- Simplified LostCard registry with hard deny at authorization.
- Backend-backed Shift lifecycle with minimal closure rules.
- FIFO keg suggestion (recommendation only, not warehouse automation).
- POSAdapter boundary in stub/log mode.

It preserves current platform principles:
- **Controller = volume source of truth**.
- **Backend = operational state source of truth**.
- Additive, non-breaking evolution of existing demo flows.

## What this pipeline intentionally does NOT build
Out of demo scope by design:
- Full alert lifecycle engine (only minimal events where required).
- Complex reconciliation policies and back-office dispute workflows.
- Full RBAC or advanced role hierarchy.
- Multi-location runtime behavior.
- Full POS financial integration/fiscal logic.
- Production redundancy and high-availability architecture.

---

## 2) Demo-Oriented Milestones

## M1 — Additive operational data foundation
**Goal**
- Introduce only the data primitives required for demo narrative.

**Exact scope**
- Add backend entities/columns for: `Visit`, `LostCard`, minimal `Shift`, `Pour.sync_status`, tap status extension (`processing_sync`, `out_of_keg`).
- Keep existing endpoints operational.

**Backend changes**
- `backend/models.py`, `backend/schemas.py`, new minimal CRUD modules as needed.
- First tracked migration set under `backend/alembic/` (additive only).

**Controller changes**
- None.

**Admin UI changes**
- None mandatory.

**What we gain for demo**
- Stable foundation for all demo-critical behaviors without UI disruption.

**What we intentionally defer**
- Full alert schema/actions.
- Any advanced reporting model.

**Risk level**: **Med** (migration baseline risk).

---

## M2 — Visit lifecycle (demo-ready)
**Goal**
- Make Visit the runtime session anchor.

**Exact scope**
- Open/close visit operations.
- Enforce one active visit per guest.
- On visit close, deactivate active card.

**Backend changes**
- Add Visit service + API (new module or guest API extension).
- Enforce invariant checks in visit open/close path.

**Controller changes**
- None yet.

**Admin UI changes**
- Minimal actions in guest workflow: Open Visit / Close Visit + current visit status badge.

**What we gain for demo**
- Strong operational story: explicit guest session control.

**What we intentionally defer**
- Rich visit analytics/history UI.

**Risk level**: **Med**.

---

## M3 — Active tap lock + anti-simultaneous usage
**Goal**
- Demonstrate anti-cloning/anti-sharing control in live flow.

**Exact scope**
- Authorization response includes allow/deny + reason.
- If visit has `active_tap_id`, deny with tap reference.
- Lock set at start, released at successful completion/sync completion.

**Backend changes**
- Lightweight controller authorization endpoint/service.
- Lock lifecycle handling in pour start/finalize path.

**Controller changes**
- Replace "card exists" check with backend authorization decision call.

**Admin UI changes**
- Minimal read-only indicator: "Card in use on Tap X" (dashboard/guest detail).

**What we gain for demo**
- Clear security/abuse prevention showcase.

**What we intentionally defer**
- Advanced conflict-resolution tooling.

**Risk level**: **High** (state consistency between lock and session end).

---

## M4 — Minimal offline sync semantics
**Goal**
- Show resilient offline behavior without complex reconciliation engine.

**Exact scope**
- Persist explicit `sync_status` on pours.
- Use `processing_sync` tap status while pending sync exists.
- Block new authorizations on tap while `processing_sync`.
- On successful sync: mark synced, clear lock, return tap to active.

**Backend changes**
- Extend sync ingestion path in `backend/main.py` and `backend/crud/pour_crud.py`.
- Minimal pending/synced state transitions only.

**Controller changes**
- Respect processing_sync denial and retry sync as currently designed.

**Admin UI changes**
- Simple pending sync counter + tap status pill.

**What we gain for demo**
- Credible offline resilience narrative with visible recovery behavior.

**What we intentionally defer**
- Deep mismatch adjudication workflows.

**Risk level**: **High** (edge-case ordering).

---

## M5 — Simplified LostCard registry + enforcement
**Goal**
- Demonstrate security incident control with minimal footprint.

**Exact scope**
- Register lost card entry linked to guest/visit when possible.
- Authorization hard-deny if UID exists in LostCard.
- Emit minimal operational event/audit line (not full alert engine).

**Backend changes**
- LostCard CRUD + check in authorization service.

**Controller changes**
- Show deny reason and keep valve closed.

**Admin UI changes**
- "Report card lost" action and simple lost-card list.

**What we gain for demo**
- Practical fraud/safety control story.

**What we intentionally defer**
- Alert ack/resolve workflows and severity matrices.

**Risk level**: **Med**.

---

## M6 — Backend shift discipline (minimal)
**Goal**
- Replace local-only shift with backend-backed operational discipline.

**Exact scope**
- Shift open/close API.
- Minimal close blockers:
  1) no active visits,
  2) no pending_sync pours.
- Return concise close precheck response.

**Backend changes**
- Minimal Shift model + service + precheck endpoint.

**Controller changes**
- None.

**Admin UI changes**
- Move `shiftStore` from localStorage authority to backend authority.
- Minimal close-check modal (not full wizard).

**What we gain for demo**
- Demonstrable operational discipline and close control.

**What we intentionally defer**
- Full shift closing wizard with inspection, alert management, and extensive reporting.

**Risk level**: **Med**.

---

## M7 — FIFO keg recommendation + POSAdapter stub boundary
**Goal**
- Finish demo narrative with inventory guidance + integration readiness.

**Exact scope**
- FIFO suggestion endpoint: same beer type, oldest warehouse keg.
- Recommendation only; staff confirms assignment manually.
- POSAdapter boundary service with stub/log implementation:
  - `notify_topup`, `notify_refund`, `notify_pour`.

**Backend changes**
- FIFO query service.
- POSAdapter interface module + stub/log adapter.

**Controller changes**
- None.

**Admin UI changes**
- Display suggested keg in assignment modal.
- Optional "POS event sent" badge/log line for demo visibility.

**What we gain for demo**
- Inventory intelligence + POS-ready architecture claim without deep coupling.

**What we intentionally defer**
- Warehouse accounting automation.
- Real POS adapter implementations.

**Risk level**: **Low-Med**.

---

## 3) Demo Capability Matrix

| Capability | Available after milestone |
|---|---|
| Demonstrate secure visit model | **M2** |
| Demonstrate anti-cloning protection (`active_tap_id`) | **M3** |
| Demonstrate offline resilience with explicit sync states | **M4** |
| Demonstrate shift discipline (backend authority + blockers) | **M6** |
| Present system as POS-ready (contract boundary) | **M7** |

---

## 4) Time/Complexity Assessment

- Relative effort vs full `PIPELINE_V1`: **~45–55%** implementation surface.
- Why reduced:
  - no full alert lifecycle,
  - no complex reconciliation engine,
  - no deep RBAC,
  - no production hardening layers.

## Riskiest milestone
- **M4 (Minimal offline sync semantics)** is riskiest due to state transitions across controller local queue, backend sync status, tap lock status, and visit unlock timing.

---

## 5) Architectural Safety Check

## No hidden production-only complexity introduced
- Confirmed: scope excludes production-hardening systems (HA, deep alert workflows, advanced reconciliation, RBAC hierarchy).

## No contradictions with `OPERATIONAL_MODEL_V1`
- Confirmed: selected features directly map to spec-critical demo flows (visit lifecycle, active tap lock, offline sync, lost card enforcement, shift discipline, FIFO guidance, POS boundary).

## No future rewrite trap
- Confirmed: all changes are additive and compatible with full pipeline expansion later.
- Deferred items remain extension points, not throwaway work:
  - minimal events can evolve into full Alert domain,
  - minimal shift precheck can evolve into full closure wizard,
  - POSAdapter stub can be replaced by real adapters without touching core domain.
