# Demo-First Verification Scenarios

Purpose: E2E validation script to run after each milestone.

Format per scenario:
- Preconditions
- Steps
- Expected result
- Evidence to capture

---

## Scenario 1 — Happy path: visit open -> pour -> sync -> visit close

**Preconditions**
- Guest exists and passes age requirement.
- Card assigned and not lost.
- Tap active with connected keg.
- Shift open.

**Steps**
1. Open visit for guest/card.
2. Authorize pour on tap.
3. Execute pour on controller.
4. Sync pour to backend.
5. Close visit.

**Expected result**
- Exactly one active visit during session, then none.
- PourSession stored with `synced`.
- Balance and keg volume updated once.
- Card deactivated on visit close.

**Evidence**
- API responses, DB rows for visit/pour, audit entries.

---

## Scenario 2 — Simultaneous use prevention (`active_tap_id`)

**Preconditions**
- Same card presented to Tap A and Tap B concurrently.

**Steps**
1. Start authorization on Tap A and obtain lock.
2. Attempt authorization on Tap B before Tap A session ends.

**Expected result**
- Tap B denied with reason "card already in use on Tap X".
- Denial logged/audited.
- No second pour session created.

**Evidence**
- Controller denial message, backend audit/event log, absence of second active session.

---

## Scenario 3 — Lost card attempt triggers enforcement

**Preconditions**
- Card marked as lost in LostCard registry.

**Steps**
1. Present lost card on controller.

**Expected result**
- Authorization denied.
- Critical alert created.
- Optional policy action (guest/card block) applied and audited.

**Evidence**
- Alert record with severity=critical, audit trail, controller response.

---

## Scenario 4 — Offline mid-pour then sync recovery

**Preconditions**
- Tap active, visit active.

**Steps**
1. Start pour with server connected.
2. Disconnect network during active pour.
3. Finish pour locally.
4. Restore network.
5. Trigger sync cycle.

**Expected result**
- Pour completes locally, persisted pending.
- Tap enters `processing_sync` and blocks new cards.
- After successful sync: pour marked synced, active lock cleared, tap returns active.

**Evidence**
- Controller local journal status transitions, backend sync-status transitions, tap state timeline.

---

## Scenario 5 — Server unavailable before pour

**Preconditions**
- Backend intentionally down.

**Steps**
1. Present card to idle tap.

**Expected result**
- New pour denied with explicit "Server unavailable" path.
- No valve open event.

**Evidence**
- Controller logs, absence of new local/remote session records.

---

## Scenario 6 — Pending sync blocks shift closure

**Preconditions**
- Shift open.
- At least one pending_sync pour exists.

**Steps**
1. Initiate shift close wizard.

**Expected result**
- Wizard blocks closure and lists pending sync items.
- After sync completion, closure can proceed.

**Evidence**
- Wizard gate output, backend close-precheck payload.

---

## Scenario 7 — Shift closure blocked by active visits

**Preconditions**
- Shift open with >=1 active visit.

**Steps**
1. Run close wizard.

**Expected result**
- Closure blocked with list/count of active visits.
- After closing visits, gate passes.

**Evidence**
- Precheck results before/after visit closure.

---

## Scenario 8 — Keg replacement FIFO suggestion

**Preconditions**
- Tap keg becomes empty.
- Warehouse has >=2 kegs of same beer type with different `received_at`.

**Steps**
1. Set tap/out-of-keg condition.
2. Open replacement flow.
3. Observe suggested keg.
4. Confirm replacement.

**Expected result**
- Suggested keg is oldest warehouse candidate.
- Status transitions: old keg disconnected/empty, new keg connected, tap active.

**Evidence**
- FIFO query output and timestamps, post-action state records.

---

## Scenario 9 — Alert lifecycle (acknowledge/resolve)

**Preconditions**
- Create warning and critical alerts (e.g., keg threshold + lost-card event).

**Steps**
1. Acknowledge alert.
2. Resolve with comment.

**Expected result**
- `acknowledged_by` and `resolved_at` populated correctly.
- Shift wizard behavior reflects unresolved/acknowledged states per policy.

**Evidence**
- Alert row transitions and audit logs.

---

## Scenario 10 — POSAdapter boundary smoke (MVP stub)

**Preconditions**
- POSAdapter configured in stub/manual mode.

**Steps**
1. Execute top-up.
2. Execute pour.
3. Execute refund (if available in current flow).

**Expected result**
- Outbound adapter notifications logged/queued.
- Core operations remain successful even if adapter fails (policy: fail-open for MVP).

**Evidence**
- Adapter logs/outbox records + successful business transaction records.

---

## Milestone-to-scenario mapping
- **M1**: baseline migration checks + scenario setup integrity.
- **M2**: Scenarios 1, 7.
- **M3**: Scenarios 4, 6.
- **M4**: Scenario 2.
- **M5**: Scenario 3.
- **M6**: Scenario 8.
- **M7**: Scenario 9.
- **M8**: Scenarios 6, 7 (+ report verification).
- **M9**: Scenario 10.

## Exit criteria for operational-model alignment
- All scenarios pass in staging at least once with retained evidence artifacts.
- No Sev-1/Sev-2 unresolved defects on scenarios 2, 3, 4, 6, 7.
