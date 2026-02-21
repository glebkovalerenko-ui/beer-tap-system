# Gap Analysis Matrix — Operational Model V1 vs Current Repo

Legend:
- **Support**: Fully / Partial / Missing
- **Complexity**: S / M / L
- **Risk**: Low / Med / High

## Matrix

| Requirement (from OPERATIONAL_MODEL_V1) | Current support status + what is needed |
|---|---|
| Guest identity model with age gate and unique passport | **Partial**. Guest exists with DOB + id document uniqueness check in CRUD, but no explicit under-18 enforcement at card issuance time. Need backend validation in guest-card binding flow + UI guardrails. **Needs**: backend + UI. **Complexity**: M. **Risk**: Med. |
| One guest = one active visit | **Missing**. No Visit entity. Need Visit schema/model/API + invariant checks. **Needs**: backend data schema + API + controller auth flow + admin UI. **Complexity**: L. **Risk**: High. **Depends on**: Visit model baseline. |
| One visit = one active card; visit close deactivates card | **Missing**. Card exists but no visit linkage/close semantics. **Needs**: backend visit lifecycle + card state transition rules + UI actions. **Complexity**: L. **Risk**: High. **Depends on**: Visit model. |
| LostCard registry with critical alert on usage | **Missing**. Only card `status=lost` exists; no separate LostCard entity or usage-triggered alert workflow. **Needs**: backend schema/API + authorization checks + alerts + UI list/action panel. **Complexity**: M-L. **Risk**: High. **Depends on**: Alert model + authorization interception. |
| Visit active_tap_id lock and simultaneous card use prevention | **Missing**. No visit lock field or denial messaging from backend. **Needs**: backend authorization service + controller response handling + UI/admin diagnostics. **Complexity**: M-L. **Risk**: High. **Depends on**: Visit lifecycle + controller auth contract update. |
| PourSession with `sync_status` (`synced`/`pending_sync`) | **Partial**. Pour table exists; no sync_status field. Controller local DB has `new/confirmed/failed`. **Needs**: backend schema extension + sync pipeline state machine + tap status coupling. **Complexity**: M. **Risk**: High. **Depends on**: Tap `processing_sync`. |
| Tap status includes `processing_sync` and blocks new cards during reconciliation | **Missing**. Tap states are `active/locked/cleaning/empty`. **Needs**: tap status enum/state transitions + controller behavior contract + monitoring UI updates. **Complexity**: M. **Risk**: Med-High. **Depends on**: pour sync model changes. |
| Offline pour continuation + deferred sync + mismatch alert | **Partial**. Local capture + later sync exists; no mismatch detection/alert entity and no explicit pending_sync semantics. **Needs**: reconciliation service + Alert integration + runbook UI. **Complexity**: L. **Risk**: High. **Depends on**: Alert model + Pour sync state + Visit lock release semantics. |
| Server unavailable behavior: block new pours, complete active pours | **Partial**. Controller blocks only by failed auth calls implicitly; no explicit mode contract or cached authorization policy. **Needs**: controller state machine + backend health endpoint contract usage + explicit UX messages. **Complexity**: M. **Risk**: High. **Depends on**: controller protocol update. |
| Keg lifecycle statuses (`warehouse/connected/empty/retired`) | **Partial**. Current statuses are `full/in_use/empty`. Missing warehouse/retired semantics and timestamps (`received_at/connected_at/disconnected_at`). **Needs**: schema + CRUD + UI updates. **Complexity**: M. **Risk**: Med. |
| FIFO keg replacement suggestion (same beer type + oldest in warehouse) | **Missing**. No recommendation service. **Needs**: backend query/service + UI hint in assign flow. **Complexity**: M. **Risk**: Med. **Depends on**: keg lifecycle enrichment. |
| Keg alert thresholds (<20% info, <10% warning, empty/flow fail critical) | **Missing**. No alert threshold evaluation engine. **Needs**: alert rule evaluator + UI alert surface + ack/resolve operations. **Complexity**: M. **Risk**: Med-High. **Depends on**: Alert model. |
| Shift entity + ShiftMember + closure constraints | **Missing** (backend). Frontend-only local shift store exists. **Needs**: backend schema/API + closure wizard checks + UI migration from localStorage to API-backed shift state. **Complexity**: L. **Risk**: High. **Depends on**: Visit + sync-status + Alert readiness. |
| Shift closing wizard steps (active visits, pending sync, unresolved alerts shown, inspection, summary, confirm) | **Missing**. Current dashboard has simple open/close and basic summary modal only. **Needs**: backend checklist endpoint + UI wizard route/modal + acceptance gating. **Complexity**: M-L. **Risk**: Med-High. **Depends on**: Shift + Visit + Alert + sync status. |
| Shift report minimum fields (visits, volume, amount, cancelled pours, unresolved alerts, lost cards, staff) | **Missing**. No shift report backend artifact. **Needs**: report query service + export/presentation layer. **Complexity**: M. **Risk**: Med. **Depends on**: Shift model + Alert + LostCard + Visit. |
| Alert model: severity + acknowledge + resolve with comments | **Missing**. No alert table/API/UI. **Needs**: backend schema/API + UI list/detail/workflow. **Complexity**: M. **Risk**: High. |
| Audit logging of sensitive operations | **Partial**. Generic audit exists for mutating API calls; missing explicit audit semantics for visit lifecycle, denied pours, lost-card enforcement, sync mismatches, shift close checks. **Needs**: backend event taxonomy expansion + targeted instrumentation. **Complexity**: M. **Risk**: Med. |
| POSAdapter contract boundary (`notify_topup/refund/pour`) | **Missing (explicit boundary)**. Financial events currently stay internal (transactions only). **Needs**: service interface + stub/manual adapter + outbound event hooks. **Complexity**: M. **Risk**: Med. **Depends on**: event points in topup/refund/pour flows. |
| MVP single unified staff role | **Partial**. Backend effectively single user; frontend has local pseudo-roles. Need consistent single-role enforcement and remove accidental divergence. **Needs**: auth model clarification + UI consistency + docs. **Complexity**: S-M. **Risk**: Low-Med. |
| Location field retained for future multi-location | **Missing**. No Location model today. **Needs**: additive schema + future-proof foreign keys where required (e.g., Shift). **Complexity**: S-M. **Risk**: Low. |

## Dependency highlights
1. **Visit model** is foundational for: active_tap lock, simultaneous-use prevention, shift close blockers, lost-card correlation.
2. **Alert model** is foundational for: lost-card critical events, sync mismatch handling, keg thresholds, shift closure UX.
3. **Pour sync-status model** is foundational for: processing_sync tap state and shift close pending-sync checks.
4. **Shift backend model** should be implemented after foundational visit/sync/alert primitives exist, otherwise wizard gates are placeholders only.

## Implementation posture recommendation
- Execute additive, backward-compatible changes first (new tables/columns and parallel APIs), then migrate controller/admin flows.
- Keep current endpoints operational while introducing `v1 operational` endpoints/contracts behind feature flags where practical.
