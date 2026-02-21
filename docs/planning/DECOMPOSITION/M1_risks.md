# M1 Migration Baseline — Risks, Safety, and Rollback

## 1) Risk Register

## R1 — Baseline mismatch with live DB
- **Description:** Initial Alembic baseline may not exactly match real pilot/dev DB schema already created via `create_all` or manual edits.
- **Likelihood:** Medium
- **Impact:** High
- **Signals:** `alembic upgrade` attempts unexpected ALTER/CREATE on existing tables; constraint/index conflicts.
- **Mitigation:**
  - Run schema diff/parity check on representative snapshot before stamp.
  - Use stamp only after parity confirmation.
  - Document mismatch remediation path.

## R2 — Dual schema writers (`create_all` + Alembic)
- **Description:** Runtime `Base.metadata.create_all` can create drift relative to migration history.
- **Likelihood:** Medium
- **Impact:** High
- **Signals:** New table/column appears without corresponding revision.
- **Mitigation:**
  - Explicit transition policy for `create_all` during/after M1.
  - Enforce “schema changes only through migrations” in PR checks.

## R3 — Env contract inconsistency
- **Description:** Backend uses `DATABASE_URL`; Alembic currently builds URL from `POSTGRES_*` vars.
- **Likelihood:** Medium
- **Impact:** Medium/High
- **Signals:** App connects successfully but Alembic fails (or vice versa) in certain environments.
- **Mitigation:**
  - Document canonical env contract.
  - Validate migration commands in docker and local shell contexts.

## R4 — False-safe stamping
- **Description:** Team may stamp baseline onto non-matching schema, hiding drift.
- **Likelihood:** Medium
- **Impact:** High
- **Signals:** Future migrations fail unexpectedly; data anomalies after seemingly successful stamp.
- **Mitigation:**
  - Stamp procedure must include required parity checks and sign-off.
  - Restrict stamp use to designated maintainers.

## R5 — Rollback not practically tested
- **Description:** Downgrade path exists on paper but is untested for real datasets.
- **Likelihood:** Medium
- **Impact:** High (pilot downtime)
- **Signals:** Migration incident with no confident reverse path.
- **Mitigation:**
  - Rehearse rollback/restore in staging snapshot.
  - Prefer backup restore when downgrade risk is uncertain.

## R6 — Pilot-time migration execution risk
- **Description:** Applying baseline during active bar operations can impact availability.
- **Likelihood:** Low/Medium
- **Impact:** High
- **Signals:** Elevated API errors/timeouts during migration window.
- **Mitigation:**
  - Execute in controlled window.
  - Pre-migration backup + rollback owner on-call.
  - Freeze non-essential writes during execution.

## R7 — Scope drift into controller SQLite migration
- **Description:** Attempting to include RPi SQLite migration in M1 increases risk and timeline.
- **Likelihood:** Medium
- **Impact:** Medium
- **Signals:** New requirements on `rpi-controller/database.py` appear mid-milestone.
- **Mitigation:**
  - Keep explicit scope boundary in M1 docs.
  - Plan controller migration discipline as separate future milestone.

---

## 2) Safety Plan (Pilot-Oriented)

### Mandatory pre-migration controls
1. Confirm migration package reviewed and approved.
2. Take full Postgres backup (timestamped and verified restorable).
3. Validate migration on staging/snapshot first.
4. Announce maintenance window + owner roles.

### Execution controls
1. Run migration commands exactly from approved runbook.
2. Monitor API health and DB logs in parallel.
3. Stop immediately on unexpected DDL/data errors.

### Post-migration controls
1. Verify current revision (`alembic current`) is expected head.
2. Run API smoke checks.
3. Confirm core read/write flows for pilot operations.
4. Archive logs and migration evidence.

---

## 3) Rollback / Recovery Decision Tree

1. **Issue detected during migration?**
   - Yes → pause writes + capture error context.
2. **Is downgrade path tested and safe for this exact revision/data state?**
   - Yes → perform controlled downgrade and re-verify.
   - No/uncertain → restore pre-migration backup.
3. **After rollback/restore:**
   - Re-run smoke checks.
   - Keep system on known-good revision.
   - Create incident note and corrective action before reattempt.

### Rollback objective
- Restore service quickly with known data integrity, prioritizing pilot continuity over rapid reattempt.

---

## 4) Ownership Matrix
- **Migration author:** prepares revision and self-checks safety.
- **Migration reviewer:** validates DDL/data safety and policy compliance.
- **Release operator:** executes runbook during approved window.
- **Pilot incident owner:** decides downgrade vs restore under time pressure.

(One person may hold multiple roles in small team, but roles must be explicitly assigned before execution.)

---

## 5) Exit Risks Allowed vs Not Allowed for M1 Completion

### Allowed residual risks after M1
- Minor process friction in developer migration ergonomics.
- Deferred CI automation hardening (if runbook + manual checks are solid).

### Not allowed at M1 exit
- No baseline revision committed.
- No validated onboarding path for existing DB.
- No tested rollback/restore procedure.
- Continued undocumented direct schema editing in production/pilot environments.
