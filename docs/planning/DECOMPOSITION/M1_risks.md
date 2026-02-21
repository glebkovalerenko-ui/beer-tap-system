# M1 Migration Baseline — Risks, Safety, and Rollback

## 1) Risk Register

## R1 — Baseline mismatch with live DB
- **Description:** Baseline revision may not match existing DBs created via prior startup behavior/manual edits.
- **Likelihood:** Medium
- **Impact:** High
- **Mitigation:** Schema parity check before `stamp`; no blind stamping.

## R2 — Incomplete cutover from `create_all` to Alembic-only
- **Description:** If `Base.metadata.create_all()` remains active, drift can continue despite migrations.
- **Likelihood:** Medium
- **Impact:** High
- **Mitigation:** Remove/disable `create_all` in M1 and verify startup path.

## R3 — Env contract inconsistency
- **Description:** App and Alembic may read different env inputs (`DATABASE_URL` vs `POSTGRES_*`).
- **Likelihood:** Medium
- **Impact:** Medium/High
- **Mitigation:** Document canonical env contract and validate in docker + local contexts.

## R4 — False-safe stamping
- **Description:** Stamping non-matching DB schema can hide drift until later migrations fail.
- **Likelihood:** Medium
- **Impact:** High
- **Mitigation:** Restrict stamp to parity-confirmed DBs and designated maintainers.

## R5 — Over-scoping rollback expectations
- **Description:** Attempting full downgrade runbook in M1 can delay pilot-readiness.
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:** Keep M1 downgrade scope minimal: one-time capability check on latest/simple revision.

## R6 — Pilot-time migration execution risk
- **Description:** Migration errors during bar operation can impact service continuity.
- **Likelihood:** Low/Medium
- **Impact:** High
- **Mitigation:** Controlled window, backup-first, operator ownership, restore-ready posture.

## R7 — Scope creep into controller SQLite migration
- **Description:** Adding controller DB migration work to M1 expands risk/timeline.
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:** Keep controller SQLite migration explicitly out-of-scope for M1.

---

## 2) Safety Plan (Pilot-Oriented)

### Pre-migration controls
1. Approved migration set and reviewers assigned.
2. Verified Postgres backup taken and restorable.
3. Rehearsal on staging/snapshot environment.
4. Migration window and operator on-call confirmed.

### Execution controls
1. Apply migrations via approved runbook.
2. Monitor API/DB logs and health checks.
3. Stop on unexpected DDL/data errors.

### Post-migration controls
1. Confirm `alembic current` at expected head.
2. Run API smoke checks.
3. Verify core pilot operational flows.
4. Archive run evidence.

---

## 3) Lightweight Rollback / Recovery Note (M1)

M1 rollback scope is intentionally minimal:
1. If failure occurs, pause writes and capture error context.
2. Use one-step downgrade **only if** it matches the tested simple/latest pattern and is clearly safe.
3. Otherwise restore pre-migration backup.
4. Re-verify service health and core flows.

This milestone does **not** require a full expanded downgrade runbook; backup-restore remains the primary safety fallback.

---

## 4) Ownership Matrix
- **Migration author:** prepares revision and self-check.
- **Migration reviewer:** validates safety and policy compliance.
- **Release operator:** executes in approved window.
- **Incident owner:** decides downgrade-if-applicable vs backup restore.

---

## 5) M1 Exit Risk Thresholds

### Allowed residual risk
- Minor process friction in migration workflow.
- Deferred broader automation hardening to post-M1.

### Not allowed at M1 exit
- `create_all` still active in runtime startup path.
- No committed baseline migration history.
- No validated existing DB onboarding path.
- No one-time downgrade capability proof.
- No backup/recovery note for pilot execution.
