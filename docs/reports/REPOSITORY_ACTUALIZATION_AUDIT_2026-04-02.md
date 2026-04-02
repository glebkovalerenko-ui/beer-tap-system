# Repository Actualization Audit (2026-04-02)

## 1. Goal

This pass analyzed the repository branch topology, separated the live delivery line from older side branches, and updated the default branch to the current verified working state without rewriting history.

## 2. Main finding

At the start of the audit, `master` was behind the active delivery line but not ahead of it:

- `master` -> `77e89f8` (`Refactor admin app to operator-first IA`)
- active line -> `feature/guest-visit-card-consolidation-sprint1`
- distance: `master..feature/guest-visit-card-consolidation-sprint1 = 14 commits`
- reverse distance: `feature/guest-visit-card-consolidation-sprint1..master = 0 commits`

That made `master` a safe fast-forward candidate.

## 3. What the active line contains

The current operator-facing line is cumulative and already includes these earlier branch tips:

- `feature/admin-app-operator-polish`
- `hotfix/admin-app-live-usability-remediation`
- `investigation/admin-app-domain-consistency-audit`
- `feature/guest-visit-card-consolidation-sprint1`

In practice this means the fast-forward to the current feature branch also absorbs:

- operator IA polish and density/copy cleanup;
- guest/visit runtime fixes;
- visit-owned card lifecycle consolidation and blocked-lost recovery;
- Syncthing project-sync verification and related deploy docs;
- Russian localization of active operator surfaces and runtime copy normalization.

## 4. Remaining non-merged islands

The repository still contains side branches that should not be auto-merged blindly:

### `fix/zero-volume-pending-sync-option-b`

- contains an alternative backend/controller contract for deferred pending-sync creation;
- carries real code and tests, not only docs;
- was not auto-merged because later history already contains a different live fix path for the user-visible `processing_sync` regression (`9fbe8e0`, already contained in `master`);
- direct integration now requires a fresh product/contract decision, not a blind merge of an older option.

### `investigation/processing-sync-recurrence-after-option-b`

- builds on the Option B branch above and adds RCA/tests for recurrence;
- remains useful as investigation context;
- should be treated as a research branch until someone explicitly decides to revive that contract.

### `foundation/tap-display-corrections`

- contains a correction package for display auth, stale precedence, media validation, kiosk startup, and encoding cleanup;
- the branch diverged before later tap-display, kiosk, and localization work landed;
- a direct merge conflicts with the current `admin-app`, `tap-display-client`, and runtime files;
- if needed, the right follow-up is selective cherry-picking of still-missing fixes, not branch-level merge.

### `integration/pi-runtime-finalize`

- one branch commit is already patch-equivalent to code now present in `master`;
- the remaining unique commit (`Pi: harden controller runtime against transient stalls`) predates later controller/runtime evolution and conflicts with newer `flow_manager` / `sync_manager` logic;
- it should be reviewed as a targeted hardening source, not merged wholesale.

### Alias / historical refs

- `pr-44`, `pr-45`, and `release/pi-runtime-master` are convenience or historical refs, not canonical integration targets;
- backup and many `codex/*` branches remain as historical artifacts and should be cleaned only with an explicit branch-retention policy.

## 5. Actualization action

The safe repository actualization for this pass is:

- fast-forward `master` to the current verified active line;
- keep the remaining side branches intact for explicit follow-up integration decisions.

## 6. Result

After this pass, the default branch reflects the current operator-facing working state, while older divergent branches remain preserved as separate context rather than being mixed into `master` without review.
