# Risks Register + Decision Log (Operational Model V1 Alignment)

## Top 10 risks and mitigations

| # | Risk | Impact | Mitigation | Owner area |
|---|---|---|---|---|
| 1 | Visit + active_tap lock inconsistency during partial failures | Unauthorized concurrent pours or stuck locks | Add lock timeout + explicit finalize/reconcile APIs + audited manual unlock | Backend + Controller |
| 2 | Offline/partial sync causes duplicate or missing pour accounting | Financial/volume mismatch | Preserve idempotency by `client_tx_id`, add `sync_status`, reconciliation job, alert on mismatch | Backend |
| 3 | Server unavailable handling is implicit and inconsistent | New pours may be attempted in undefined state | Define explicit controller state machine for server-down mode; block new sessions, allow in-flight completion | Controller |
| 4 | No first-class Visit model migration path | Hard-to-enforce invariants | Add Visit additively with backward-compatible card flow, then switch controller auth gradually | Backend + UI |
| 5 | Lost-card enforcement false positives (UID normalization differences) | Legitimate guests blocked or security holes | Standardize UID normalization backend+controller; add diagnostic logs and operator override workflow | Backend + Controller |
| 6 | Shift closure wizard introduced before data primitives | Operational dead-ends or fake gating | Sequence implementation: Visit + sync + alerts before hard shift blockers | Product + Engineering |
| 7 | Alert volume too noisy | Alert fatigue and ignored critical events | Start with minimal deterministic rule set and thresholds; tune after pilot telemetry | Backend + Ops |
| 8 | Schema migration risk (no alembic versions currently tracked) | Deploy instability / rollback pain | Create migration baseline, rehearse upgrade/downgrade, DB backup before each rollout | Backend/DevOps |
| 9 | Source-of-truth ambiguity (controller vs backend) | Reconciliation disputes and manual correction burden | Codify rule: controller volume truth, backend operational state truth; add explicit conflict policy | Product + Backend |
| 10 | POSAdapter coupling introduces transactional fragility | Core operations fail due to external POS errors | MVP adapter fail-open with outbox/log queue and retry; keep core commit independent | Backend |

---

## Special attention scenarios

## A) Offline / partial-sync edge cases
- **Case**: pour ends offline, backend reconnect delayed.
- **Default handling**:
  1. store local pour as pending,
  2. backend records `pending_sync` on intake/recovery path,
  3. maintain lock semantics until reconciliation result deterministic,
  4. emit alert only if mismatch or timeout threshold reached.

## B) Server unavailability
- **Case**: backend unreachable pre-pour.
- **Default handling**: deny new authorizations immediately with explicit controller UX message "Server unavailable".
- **Case**: backend unreachable mid-pour.
- **Default handling**: finish active pour, persist locally, enter processing sync mode.

## C) Manual reconciliation during controller offline
- **Case**: staff manually adjusts balance while controller queues unsynced pours.
- **Default handling**:
  - keep immutable transaction trail,
  - reconcile by event timestamp ordering,
  - if post-sync balance differs from expected envelope -> `BalanceMismatch` alert + review queue.

## D) Source of truth and consistency
- **Recommended MVP contract**:
  - Controller = source of truth for measured volume.
  - Backend = source of truth for guest state, visit locks, card validity, shift status, alert status.
  - Reconciliation engine = mediator for eventual consistency and mismatch signaling.

## E) Migration strategy if DB schema changes are required
- Phase migrations as additive first:
  1. create new tables/columns nullable or defaulted,
  2. deploy code that dual-reads old/new,
  3. backfill data,
  4. switch write path,
  5. enforce constraints.
- Always ship rollback SQL + snapshot backup instructions.

---

## Open decisions + recommended MVP defaults

| Decision topic | Options | Recommended MVP default | Rationale |
|---|---|---|---|
| Visit opening trigger relative to POS | open-before-pos vs open-after-pos | **Open after POS confirmation** | Matches spec sequence and avoids orphan active visits |
| Lost card data model | card status only vs separate LostCard registry | **Separate LostCard registry + card status sync** | Preserves history and event provenance |
| Sync mismatch severity | warning always vs severity by delta threshold | **Threshold-based (small=warning, large=critical)** | Reduces noise while surfacing major issues |
| Tap unlock policy after offline pour | unlock on local completion vs unlock after backend reconciliation | **Unlock after backend reconciliation** | Stronger safety against concurrent misuse |
| Shift closure on critical alerts | block closure vs require acknowledgement only | **Do not block, require acknowledgment** | Spec-compliant and operationally practical |
| POSAdapter failure policy | fail-close vs fail-open | **Fail-open with audited queue** | Keeps bar operations running in MVP |
| Role model in MVP | pseudo-multi-role vs unified role | **Unified staff role enforced backend-side** | Aligns with spec MVP and reduces confusion |
| Keg FIFO source timestamp | `received_at` vs `created_at` fallback | **`received_at`, fallback to created_at until backfilled** | Practical migration path |
| Reconciliation execution model | synchronous on sync endpoint vs async worker | **Synchronous first, async later if load requires** | Simpler correctness-first MVP |
| Location support | skip entirely vs add single default location | **Add single default location row and FK-ready schema** | Future-proof with minimal complexity |
