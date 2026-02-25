# Pilot-Ready Demo Pipeline вЂ” OPERATIONAL_MODEL_V1 Alignment

## 1) Executive Summary

## What this pipeline ensures for pilot safety
This roadmap preserves demo speed while making the system safe for a real pilot bar:
- **Visit is the invariant root** (one active visit per guest).
- **Active tap lock** prevents simultaneous card usage.
- **Offline behavior is deterministic** (`sync_status`, `processing_sync`, explicit unlock rules).
- **Shift lifecycle is backend-authoritative** (daily operations are controlled centrally, not by local UI state).
- **Schema evolution is migration-controlled** (baseline + additive-first + rollback discipline).
- **POS integration remains isolated** behind a stub boundary so core domain stays independent.

It preserves architecture:
- Controller = source of truth for measured volume.
- Backend = source of truth for operational state transitions.

## What this pipeline intentionally postpones
Out of scope (intentionally):
- Full alert lifecycle engine.
- Complex reconciliation platform.
- Enterprise RBAC / advanced role hierarchy.
- Multi-location runtime logic.
- Deep POS transactional/fiscal integration.
- HA/redundancy architecture.

---

## 2) Refined Milestones (Pilot-Ready)

## M1 вЂ” Migration baseline + additive schema guardrails
**Goal**
- Introduce real migration discipline before pilot-critical behavior changes.

**Scope**
- Establish Alembic (or equivalent) baseline for current schema.
- Define additive-first migration rules and rollback workflow.
- Freeze direct/manual schema edits outside migration scripts.

**Schema impact**
- Baseline revision, no destructive schema changes.

**Migration strategy impact**
- This milestone is the migration discipline start point for all subsequent work.

**Backend changes**
- `backend/alembic/` baseline revision(s).
- Short migration workflow notes for developers.

**Controller changes**
- None.

**Admin UI changes**
- None.

**Operational risk level**
- **Med** (baseline correctness risk).

**Demo value gained**
- Pilot credibility: controlled, repeatable schema evolution.

**Acceptance criteria (measurable)**
1. Clean DB bootstrap works from baseline to head.
2. Migration path runs on an existing DB snapshot (or documented snapshot upgrade procedure is validated).
3. Developer workflow documented and tested: create migration, apply migration, rollback migration.

---

## M2 вЂ” Visit model as invariant root
**Goal**
- Make Visit the canonical operational session.

**Scope**
- Implement open/close visit operations.
- Enforce one active visit per guest.
- Deactivate card on visit close.

**Schema impact**
- Add `visits` table with status/timestamps/reason and nullable `active_tap_id`.

**Migration strategy impact**
- Additive table introduction; no destructive changes.

**Backend changes**
- Visit model/schema/CRUD/API.
- Server-side invariant checks.

**Controller changes**
- None yet.

**Admin UI changes**
- Minimal controls: Open Visit / Close Visit and current visit state display.

**Operational risk level**
- **Med**.

**Demo value gained**
- Strong operational narrative: explicit lifecycle per guest visit.

**Acceptance criteria**
- Attempting a second active visit for same guest is rejected.
- Closing visit deactivates card and records close reason.

---

## M3 вЂ” Active tap lock semantics (anti-simultaneous usage)
**Goal**
- Enforce anti-cloning behavior in real-time authorization.

**Scope**
- Authorization returns allow/deny + reason.
- Set `active_tap_id` at authorization/start.
- Deny authorization if `active_tap_id` already set for another tap.

**Schema impact**
- Uses `visits.active_tap_id` from M2.

**Migration strategy impact**
- Behavior controlled via feature flag; schema remains additive.

**Backend changes**
- Lightweight controller authorization endpoint/service.
- Event/audit entry for denied simultaneous-use attempts.

**Controller changes**
- Replace list-scan card auth with backend authorization call.

**Admin UI changes**
- Read-only lock indicator (e.g., вЂњCard in use on Tap XвЂќ).

**Operational risk level**
- **High** (lock lifecycle consistency).

**Demo value gained**
- Demonstrable anti-sharing control for pilot and investor demos.

**Acceptance criteria**
- Concurrent second authorization with same active visit is denied.
- Lock is visible and auditable.

---

## M3.5 вЂ” Visit-Centric Operator UI (Functional Layer)
**Goal**
- Make visit the operational center of operator workflows in admin-app.

**Scope**
- Primary action: open new visit by guest (card is optional at open step).
- Active visit search by one universal query input (backend determines query type).
- Central visit card with guest identity, status, balance, and active tap lock visibility.
- Manual operator actions: force unlock (with reason) and close visit.
- Keep existing admin-app shell/layout; no global redesign and no final POS styling.
- Card issuance/binding remains a separate later step.

**UI strategy note**
- This is a functional operator layer that mirrors backend invariants.
- Final demo POS UI is intentionally deferred to a later milestone.

**Backend changes**
- None (consume existing visit APIs only).

**Controller changes**
- None.

**Admin UI changes**
- Visit-centric route/page with explicit lock-state visibility and manual intervention controls.

**Operational risk level**
- **Med**.

**Demo value gained**
- Operator can manage active visits deterministically through UI with explicit lock handling.

**Acceptance criteria**
- Operator can start from "Open new visit", find a guest, and open visit card.
- Operator can find an active visit via one search field and open visit card.
- Lock state is clearly visible (`Locked on tap #X` / `No active tap`).
- Force unlock requires reason and is executable from visit card.
- Visit can be closed from visit card.

**РћРіСЂР°РЅРёС‡РµРЅРёСЏ M3.5**
- Р’С‹РґР°С‡Р° РЅРѕРІРѕР№ РєР°СЂС‚С‹ РїСЂРё РѕС‚РєСЂС‹С‚РёРё РІРёР·РёС‚Р° (Issue Card) РЅРµ СЂРµР°Р»РёР·РѕРІР°РЅР°; РІ UI РѕСЃС‚Р°РІР»РµРЅР° Р·Р°РіР»СѓС€РєР°.
- Flow `Р’С‹РґР°С‚СЊ РєР°СЂС‚Сѓ` Р±СѓРґРµС‚ СЂРµР°Р»РёР·РѕРІР°РЅ СЃР»РµРґСѓСЋС‰РёРј С€Р°РіРѕРј РїРѕСЃР»Рµ M3.5 РєР°Рє РѕС‚РґРµР»СЊРЅС‹Р№ СЃС†РµРЅР°СЂРёР№.

---

## M4 вЂ” Minimal deterministic offline sync + manual close/reconcile (pilot scope)
**Goal**
- Handle network loss safely without building a complex reconciliation engine.

**Scope**
- Add `sync_status` (`pending_sync` / `synced`) to pour records.
- Tap enters `processing_sync` while unresolved sync exists.
- Backend clears `active_tap_id` only after backend-accepted completion/reconciliation.
- Add minimal manual close + reconcile path for timeout cases.

**Required lock/offline behavior (explicit rules)**
1. Controller can detect pour end, but **only backend changes visit/card operational state**.
2. If network is lost mid-pour:
   - pour completes using local balance,
   - controller retries sync,
   - backend keeps card locked (`active_tap_id` not cleared) until sync/reconcile,
   - new pours on other taps are blocked by design.
3. If sync does not complete within timeout window (target 1вЂ“5 minutes):
   - tap remains `processing_sync`,
   - controller UI shows `volume_ml`, `cost`, and short pour identifier (e.g., 6-digit code),
   - staff may manually enter this pour in POS/admin terminal to unlock continued use.
4. If original controller sync arrives later:
   - backend matches by pour identifier,
   - if matched -> mark reconciled,
   - if mismatch -> create minimal review alert/event.

**Schema impact**
- Add `pours.sync_status`.
- Add pour short identifier field (or deterministic derived key) for manual reconcile matching.
- Extend tap status domain with `processing_sync`.

**Migration strategy impact**
- Additive columns/status extension with default-safe values.

**Backend changes**
- Sync endpoint transition rules.
- Minimal reconcile match logic by pour identifier.
- Minimal event emission for mismatch review (not full alert engine).

**Controller changes**
- Respect `processing_sync` blocking behavior.
- Show timeout-state details (volume/cost/short id).
- Continue retrying sync in background.

**Admin UI changes**
- Pending sync indicator.
- Minimal manual entry/reconcile action path for timed-out pours.

**Operational risk level**
- **High** (**highest operational risk milestone**).

**Demo value gained**
- Credible offline resilience with deterministic pilot-safe fallback.

**Acceptance criteria**
- Card remains locked after offline pour until backend sync/reconcile.
- Timeout path displays required fields and enables manual close.
- Late sync correctly resolves by identifier or emits mismatch event.

---

## M5 вЂ” Backend-backed Shift lifecycle (minimal daily discipline)
**Goal**
- Introduce daily operational discipline before security enhancements.

**Scope**
- Shift open/close API with backend authority.
- Minimal close blockers:
  1) no active visits,
  2) no pending_sync pours.
- Minimal close precheck response.

**Schema impact**
- Add `shifts` table (minimal fields only).

**Migration strategy impact**
- Additive table; no destructive change.

**Backend changes**
- Shift model/service/API.
- Close precheck endpoint.

**Controller changes**
- None.

**Admin UI changes**
- Shift store becomes backend-authoritative.
- Minimal precheck modal for close action.

**Operational risk level**
- **Med**.

**Demo value gained**
- Strong POS/pilot credibility: controlled shift discipline.

**Acceptance criteria**
- Shift close is blocked when active visits exist.
- Shift close is blocked when pending sync exists.

---

## M6 вЂ” Simplified LostCard registry + enforcement
**Goal**
- Add pragmatic card-loss abuse prevention for pilot operation.

**Scope**
- LostCard report/list.
- Authorization hard-deny when UID is in LostCard.
- Minimal operational event/audit on blocked use.

**Schema impact**
- Add `lost_cards` table.

**Migration strategy impact**
- Additive table introduction.

**Backend changes**
- LostCard CRUD + auth check hook.

**Controller changes**
- Show clear deny reason and keep valve closed.

**Admin UI changes**
- вЂњReport Lost CardвЂќ action + basic list.

**Operational risk level**
- **Med**.

**Demo value gained**
- Operational security control without overengineering.

**Acceptance criteria**
- Lost card attempt is denied and logged.
- Lost card can be reported and listed via admin UI.

---

## M7 вЂ” FIFO keg suggestion + POSAdapter boundary (stub mode)
**Goal**
- Complete pilot demo story: inventory guidance + POS-ready architecture seam.

**Scope**
- FIFO recommendation endpoint (same beer type, oldest warehouse keg).
- Recommendation-only workflow; operator confirms manually.
- POSAdapter interface with stub/log implementation only:
  - `notify_topup`, `notify_refund`, `notify_pour`.

**Schema impact**
- Minimal keg metadata additions only if required for FIFO ordering.

**Migration strategy impact**
- Additive metadata columns with defaults.

**Backend changes**
- FIFO query service.
- POSAdapter interface + stub adapter wiring.

**Controller changes**
- None.

**Admin UI changes**
- Show suggested keg in assignment flow.
- Optional POS event indicator for demo visibility.

**Operational risk level**
- **Low-Med**.

**Demo value gained**
- вЂњPOS-ready, not POS-dependentвЂќ positioning.

**Acceptance criteria**
- FIFO suggestion deterministic for same beer type candidates.
- Stub notifications emitted for top-up/refund/pour paths.

---

## Safe rollout order and feature flags

## Safe rollout order
1. M1 вЂ” Migration baseline
2. M2 вЂ” Visit model
3. M3 вЂ” Active tap lock
4. M4 вЂ” Offline sync + manual close/reconcile
5. M5 вЂ” Backend Shift lifecycle
6. M6 вЂ” LostCard enforcement
7. M7 вЂ” FIFO + POSAdapter stub

## Recommended feature flags
- `FF_VISIT_ENFORCEMENT` (M2)
- `FF_ACTIVE_TAP_LOCK` (M3)
- `FF_SYNC_STATUS_ENFORCEMENT` (M4)
- `FF_MANUAL_POUR_RECONCILE` (M4)
- `FF_BACKEND_SHIFT_AUTHORITY` (M5)
- `FF_LOST_CARD_ENFORCEMENT` (M6)
- `FF_POS_ADAPTER_STUB` (M7)

Flags are the first rollback lever; schema rollback is secondary.

---

## 3) Migration Strategy

## 3.1 Baseline introduction (Alembic or equivalent)
1. Snapshot current schema and a representative data snapshot.
2. Create baseline revision representing current production-like state.
3. Validate baseline on:
   - clean DB bootstrap,
   - snapshot upgrade path.
4. Lock policy: all future schema changes via migration scripts only.

## 3.2 Existing schema handling
- Do not drop/rename core tables during pilot phase.
- Introduce new structures additively.
- Keep compatibility paths while feature flags are off.

## 3.3 Additive migration pattern
- Add new columns/tables nullable or default-safe.
- Deploy code that can read/write safely during transition.
- Backfill only when required, in small reversible batches.
- Enforce stricter constraints after backfill verification.

## 3.4 Rollback strategy
- Step 1: rollback behavior with feature flags.
- Step 2: if required, execute tested migration downgrade.
- Step 3: restore DB backup for severe rollback events.
- No destructive migrations in pilot roadmap.

---

## 4) Pilot Safety Considerations

## Data integrity guarantees
- Single active visit invariant enforced server-side.
- Backend-authoritative lock lifecycle (`active_tap_id`).
- Idempotent pour ingestion via `client_tx_id`.

## Offline behavior guardrails
- Active pour may complete locally.
- New cross-tap pours blocked while backend lock remains.
- `processing_sync` is explicit and visible.
- Timeout path provides manual close + later reconcile using pour identifier.

## Lock recovery strategy
- Normal recovery: sync/reconcile clears lock.
- Stale lock fallback: audited manual unlock action.

## Manual escape hatches (minimal)
- Audited force-clear `active_tap_id` for verified stale locks.
- Audited tap state reset from `processing_sync` after manual resolution.

## Controller async principle (operational guidance)
Controller tasks should remain non-blocking in pilot operation:
- card read loop,
- backend availability check,
- flow meter sampling,
- sync retry.

No major controller rewrite is proposed; this is an execution/testing guidance requirement.

---

## 5) Demo Capability Matrix (Pilot-Ready)

| Capability | Available after milestone |
|---|---|
| Demonstrate secure visit model | **M2** |
| Demonstrate anti-cloning protection | **M3** |
| Demonstrate deterministic offline resilience + manual close/reconcile | **M4** |
| Demonstrate shift discipline (backend authority) | **M5** |
| Demonstrate lost-card operational control | **M6** |
| Present system as POS-ready (stub boundary) | **M7** |

---

## 6) Architectural Integrity Check

## No future rewrite trap
- Additive schema, feature flags, and isolated adapter boundaries preserve forward evolution.

## No contradictory state models
- Visit is session root.
- Backend controls lock/unlock and tap sync states.
- Controller remains volume source only.

## No hidden enterprise complexity
- No enterprise RBAC, no full alert engine, no distributed multi-node sync, no deep POS coupling.

## No breaking of OPERATIONAL_MODEL_V1 invariants
- Pipeline maintains visit lifecycle, anti-simultaneous use, offline sync discipline, shift closure discipline, and POS boundary isolation within pilot/demo scope.

## M4 Implementation Contract Update (2026-02-25)
- `pours.sync_status` default is `synced` (safe default for legacy and happy-path rows).
- `pending_sync` is used only for explicit offline workflows.
- `pours.short_id` is mandatory in sync payload and manual reconcile payload.
- Manual reconcile is idempotent by `(visit_id, short_id)`; repeated requests return existing manual result.
- Explicit no-double-charge rule:
  - late sync checks existing manual pour by `(visit_id, short_id)`;
  - match -> audit `late_sync_matched`, no additional debit;
  - mismatch -> audit `late_sync_mismatch`, no additional debit.
- Pilot-safe uniqueness: unique DB index `(visit_id, short_id)` (`short_id IS NOT NULL`).
- Backend returns `visits.lock_set_at`; timeout/button decision is handled in UI/controller.
- Acceptance criteria for M4 completion:
  1. lock is kept until backend-accepted sync or manual reconcile;
  2. manual reconcile unlocks visit and is idempotent;
  3. late sync never creates a second charge.

