# Documentation Index

## Start here

1. [`PROJECT_STATUS.md`](../PROJECT_STATUS.md)
2. `README.md`
3. `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`
4. `docs/architecture/OPERATIONAL_MODEL_V1.md`
5. `docs/API_REFERENCE.md`

## Core system docs

- `docs/operator/state-model.md`: unified TapState/SessionState/IncidentState transitions and UI↔backend status dictionary.
- `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`: consolidated architecture for the frozen M1-M7 stage.
- `docs/architecture/OPERATIONAL_MODEL_V1.md`: operational invariants and state transitions.
- `docs/API_REFERENCE.md`: practical API contract for admin flows and controller sync.

## Developer runbooks

- `docs/dev/SYNCTHING_DEV_RUNBOOK.md`: Windows -> Syncthing -> Linux workflow.
- `docs/dev/ADMIN_APP_BACKEND_URL.md`: runtime/backend URL model for web/dev and Tauri.
- `docs/dev/GIT_HYGIENE_RUNBOOK.md`: repository hygiene conventions.
- `docs/dev/ENCODING_GUARD.md`: encoding guard expectations and usage.

## Stage closing reports

- `docs/admin-app/11-operator-action-safety-result.md`: implemented result of the shared operator safety layer, policy-driven risky actions, and additive audit/action-policy contracts.
- `docs/admin-app/10-operator-hardening-phase-3-result.md`: implemented result of operator sessions, realtime/degraded mode, and system-health hardening in the Admin App.
- `docs/admin-app/09-operator-projections-phase-2-result.md`: implemented result of the operator projection layer for `Today`, `Taps`, and `Cards & Guests`.
- `docs/reports/REPOSITORY_ACTUALIZATION_AUDIT_2026-04-02.md`: audit of hanging branches and safe actualization of the default branch to the current verified working line.
- `docs/reports/RUS_LOCALIZATION_ACTIVE_SURFACES_2026-04-02.md`: closure report for Russian localization of active operator surfaces, runtime copy normalization, and tap-display user-facing fallbacks.
- `docs/reports/RUS_LOCALIZATION_PHASE1_IMPLEMENTATION.md`: report for Phase 1 Russian display-layer localization.
- `docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md`: RCA and fix for stale hub backend, stopped Windows sender, and runtime-media drift in Syncthing.
- `docs/reports/STAGE_COMPLETION_VERDICT_PRE_NEXT_PHASE.md`: closing verdict before the next implementation phase.
- `docs/reports/REPOSITORY_CLEAN_STATE_AND_ARCHITECTURE_FREEZE.md`: final repository clean-state and architecture freeze report.
- `docs/reports/M7_VERIFICATION.md`: M7-specific verification notes.
- `docs/reports/POST_M6_PRE_M7_AUDIT.md`: historical audit that preceded M7.

## Legacy and historical docs

- `docs/mvp/`, `docs/planning/`, and older reports are historical context, not primary entry points.
- Some older documents still contain encoding debt or historical assumptions. When they conflict with current guidance, prefer `README.md` plus the documents listed under `Start here`.
