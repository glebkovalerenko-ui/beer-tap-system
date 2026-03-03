# Git Audit Report

Date: 2026-03-03
Repository: `beer-tap-system`
Remote: `origin = https://github.com/glebkovalerenko-ui/beer-tap-system.git`
Audit scope: local git state, `origin`, GitHub PRs, branch hygiene, safe cleanup

## Executive Summary

- Initial state had 21 local branches, dozens of stale remote branches, and 0 open PRs.
- `master` was clean and matched `origin/master` at `7630de9622e3a8988c7ede574010be34859a0a65`.
- Two active branches with real unpublished work were preserved as PRs:
  - PR #39 `incident/free-pour-zero-balance`
  - PR #40 `infra/syncthing-dev-workflow`
- Stale branches with unique commits but no safe merge path were preserved under `origin/backup/*`.
- Merged and obsolete branches were deleted locally and on GitHub.
- Final local branch set is minimal: `master`, `incident/free-pour-zero-balance`, `infra/syncthing-dev-workflow`.
- Final open PR set is minimal and healthy: PR #39 and PR #40, both `MERGEABLE`.
- Alembic final check on `2026-03-03`: one head, `0012_m6_rejected_sync`.

## Step 1. Facts Collected

### Initial local state

`git status --short --branch`

```text
## infra/syncthing-dev-workflow...origin/infra/syncthing-dev-workflow [ahead 1]
```

`git remote -v`

```text
origin  https://github.com/glebkovalerenko-ui/beer-tap-system.git (fetch)
origin  https://github.com/glebkovalerenko-ui/beer-tap-system.git (push)
```

### Initial branch situation

Key local branches before cleanup:

| Branch | Tracking | State |
| --- | --- | --- |
| `master` | `origin/master` | clean, in sync |
| `infra/syncthing-dev-workflow` | `origin/infra/syncthing-dev-workflow` | ahead 1 |
| `incident/free-pour-zero-balance` | `origin/incident/free-pour-zero-balance` | in sync |
| `m5-time-db-source` | `origin/m5-time-db-source` | ahead 24 |
| `pr-25`, `pr-26`, `pr-27`, `tmp-*` | none | stale local-only helpers |

Key remote branches before cleanup:

- many merged `codex/*` branches still existed on `origin`
- several milestone branches already merged through PR but not deleted
- several stale branches had unique commits and no PR:
  - `incident/free-pour-zero-balance`
  - `infra/syncthing-dev-workflow`
  - `infra/tilt-stabilize`
  - `m5-time-db-source`
  - `m6-lost-cards`
  - `m6/controller-terminal-ux`
  - `pr-28`
  - `tilt-fix-config-sync`
  - `broken-state-backup`

### History and refs

`git rev-parse HEAD` at audit start:

```text
207186cdb4d769cb01467d8e295dda168a76f8bf
```

`git rev-parse origin/master`:

```text
7630de9622e3a8988c7ede574010be34859a0a65
```

Initial `git log --oneline origin/master..HEAD` on the starting branch:

```text
207186c Add Syncthing end-to-end completion report
3008677 Document Linux Syncthing pilot setup
8cfdeac Replace Tilt docs with Syncthing dev workflow
c7297f7 Docs: document admin server url settings and UX rules
e8928e2 Admin-app: fix server settings button not submitting login
f01347a Docs: add server url configuration runbook
fd48559 Admin-app: add Settings UI for server URL
600917b Admin-app: centralize backend base URL resolution
c8f05ab Tauri: persist server base URL and add test connection command
228d269 Docs: add Tilt stabilization report and runbook
7fd128f Controller: log backend target and add startup health ping
b6c0789 Admin-app: unify API base URL for dev/build/tauri (no localhost fallback)
00d4eda Infra: stabilize postgres readiness and backend DB URL under Tilt
```

### PR state before cleanup

Initial `gh pr list --state open`:

```json
[]
```

Closed PR review showed:

- merged PRs: `#1-8`, `#10-23`, `#25-38`
- closed unmerged PRs with surviving source branches:
  - `#9` `codex/conduct-full-repository-audit-rwij6k`
  - `#24` `codex/decompose-milestone-m1-into-actionable-plan-t126xb`
  - `#37` `m6/controller-terminal-ux`

### Prune and remote cleanup signals

`git fetch --all --prune` automatically removed:

- `origin/m6/controller-terminal-ux-clean`
- `origin/m6/insufficient-funds-clamp`

Initial `git remote prune origin --dry-run` returned nothing after fetch.

## Step 2. Classification

### A. Branches/PRs already merged

These were safe to delete because the PR was merged into `master` or the branch was patch-equivalent to `master`.

| Branch or group | PR | Action |
| --- | --- | --- |
| `codex/conduct-full-repository-audit*` except `-rwij6k` | `#1-8` merged | deleted remote |
| `codex/create-execution-pipeline-for-operational-model*` | `#17-20` merged | deleted remote |
| `codex/decompose-milestone-m1-into-actionable-plan*` except `-t126xb` | `#21-23` merged | deleted remote |
| `codex/document-current-state-of-admin-app*` | `#10-16` merged | deleted remote |
| `codex/implement-visit-centric-operator-ui` | `#28` merged | deleted remote |
| `codex/plan-implementation-for-milestone-m1` | `#25` merged | deleted remote |
| `codex/plan-m2-visit-model-and-invariants` | `#26` merged | deleted remote |
| `codex/plan-m3-active-tap-lock-semantics` | `#27` merged | deleted remote |
| `m4-offline-sync-reconcile` | `#29` merged | deleted local + remote |
| `m4/stabilize-runtime-sync` | `#30` merged | deleted local + remote |
| `m5-db-time-source-clean` | `#35` merged | deleted local + remote |
| `m5-reports-xz` | `#32` merged | deleted local + remote |
| `m5-shift-operational-mode` | `#31` merged | deleted local + remote |
| `m6-db-time-duration-clean` | `#34` merged | deleted local + remote |
| `m6-lost-cards-clean` | `#33` merged | deleted local + remote |
| `pr-25`, `pr-26` | local leftovers of merged work | deleted local |
| `tmp-38-onto-36` | local helper, fully integrated | deleted local |

### B. Open and current work

| Branch | PR | State | Action |
| --- | --- | --- | --- |
| `incident/free-pour-zero-balance` | [#39](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/39) | active hotfix, initially conflicting | rebased, conflicts resolved, force-pushed with `--force-with-lease`, PR now `MERGEABLE` |
| `infra/syncthing-dev-workflow` | [#40](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/40) | active infra/docs branch | pushed and opened PR, PR `MERGEABLE` |

### C. Branches without PR

| Branch | Unique commits vs `master` | Resolution |
| --- | --- | --- |
| `infra/tilt-stabilize` | yes, but fully contained in `infra/syncthing-dev-workflow` | deleted local + remote as superseded |
| `m5-time-db-source` | yes, stale mixed history | saved as `backup/m5-time-db-source-2026-03-03`, then deleted |
| `m6-lost-cards` | yes, stale predecessor of clean branch | saved as `backup/m6-lost-cards-2026-03-03`, then deleted |
| `m6/controller-terminal-ux` | yes, PR #37 closed unmerged | saved as `backup/m6-controller-terminal-ux-2026-03-03`, then deleted |
| `pr-27` | yes, local-only unique helper history | saved as `backup/pr-27-2026-03-03`, then deleted local |
| `pr-28` | yes, orphan branch with unique commits | saved as `backup/pr-28-2026-03-03`, then deleted local + remote |
| `tmp-36-onto-38` | one unique patch remained | saved as `backup/tmp-36-onto-38-2026-03-03`, then deleted local |
| `tilt-fix-config-sync` | unique single stale commit | saved as `backup/tilt-fix-config-sync-2026-03-03`, then deleted local + remote |
| `broken-state-backup` | intentional backup snapshot | kept as-is |

### D. Dangerous situations found

| Situation | Risk | Resolution |
| --- | --- | --- |
| `infra/syncthing-dev-workflow` local branch ahead of origin by 1 | unpublished local commit | pushed and opened PR #40 |
| `incident/free-pour-zero-balance` had unique work with no PR | orphaned hotfix | opened PR #39 |
| `incident/free-pour-zero-balance` conflicted with `master` | PR not mergeable | rebased, resolved conflicts, force-pushed safely |
| `m5-time-db-source` local ahead 24, remote stale | easy to lose mixed unreleased patches | saved under `backup/*`, deleted original |
| closed PR branches `#9`, `#24`, `#37` still had surviving source refs | stale hidden history | preserved as backup where needed, then cleaned originals |

## Step 3. Actions Performed

### PRs created

- Created PR #39: `incident/free-pour-zero-balance -> master`
- Created PR #40: `infra/syncthing-dev-workflow -> master`

### Backup branches created on origin

- `backup/codex-conduct-full-repository-audit-rwij6k-2026-03-03`
- `backup/codex-decompose-milestone-m1-t126xb-2026-03-03`
- `backup/m5-time-db-source-2026-03-03`
- `backup/m6-controller-terminal-ux-2026-03-03`
- `backup/m6-lost-cards-2026-03-03`
- `backup/pr-27-2026-03-03`
- `backup/pr-28-2026-03-03`
- `backup/tilt-fix-config-sync-2026-03-03`
- `backup/tmp-36-onto-38-2026-03-03`

### Remote branches deleted

- merged `codex/*` branches listed in section A
- obsolete milestone branches listed in section A
- superseded or preserved-via-backup branches listed in section C

### Local branches deleted

- all merged milestone branches listed in section A
- local helper branches `pr-25`, `pr-26`, `pr-27`, `pr-28`, `tmp-36-onto-38`, `tmp-38-onto-36`
- local copies of all `backup/*` branches after successful push to origin
- obsolete local branches preserved remotely through backup or PR

### Incident PR conflict resolution

Rebase work performed on `incident/free-pour-zero-balance`:

- resolved conflicts in `backend/api/visits.py`
- resolved conflicts in `backend/crud/pour_crud.py`
- kept current controller logic in `rpi-controller/flow_manager.py`
- merged test coverage into `rpi-controller/test_flow_manager.py`
- kept and adapted `backend/tests/test_incident_free_pour_zero_balance.py`
- resolved doc conflicts in:
  - `docs/API_REFERENCE.md`
  - `docs/INTERFACE_CONTRACT.md`

Validation run during rebase:

- `python -m pytest backend/tests/test_incident_free_pour_zero_balance.py` -> passed `2/2`
- `python -m pytest rpi-controller/test_flow_manager.py` -> passed `4/4`

## Commands Executed

Core audit commands:

```text
git status --short --branch
git remote -v
git fetch --all --prune
git branch -vv
git for-each-ref --format="..."
git log --oneline --decorate -n 30
git rev-parse HEAD
git rev-parse origin/master
git log --oneline origin/master..HEAD
git remote prune origin --dry-run
git branch -r
gh pr list --state open
gh pr list --state closed --limit 30
gh pr list --state all --limit 200 --json ...
gh pr view 39 --json ...
gh pr view 40 --json ...
python -m alembic heads
```

Classification helpers:

```text
git log --oneline origin/master..origin/<branch>
git log --oneline origin/<branch>..<local-branch>
git cherry origin/master <branch>
git branch --merged origin/master
git branch -r --merged origin/master
git merge-base --is-ancestor ...
```

Cleanup and preservation:

```text
git branch -f backup/<name> <source>
git push -u origin backup/<name>
gh pr create --base master --head <branch> ...
git push origin infra/syncthing-dev-workflow
git push origin --delete <branch>
gh api -X DELETE /repos/glebkovalerenko-ui/beer-tap-system/git/refs/heads/<branch>
git branch -D <branch>
git fetch --all --prune
git checkout incident/free-pour-zero-balance
git rebase master
git -c core.editor=true rebase --continue
git push --force-with-lease origin incident/free-pour-zero-balance
```

## Final State

### Local branches

`git branch -vv`

```text
incident/free-pour-zero-balance 1ff7a39 [origin/incident/free-pour-zero-balance]
infra/syncthing-dev-workflow    207186c [origin/infra/syncthing-dev-workflow]
master                          7630de9 [origin/master]
```

### Remote branches

`git branch -r`

```text
origin/HEAD -> origin/master
origin/backup/codex-conduct-full-repository-audit-rwij6k-2026-03-03
origin/backup/codex-decompose-milestone-m1-t126xb-2026-03-03
origin/backup/m5-time-db-source-2026-03-03
origin/backup/m6-controller-terminal-ux-2026-03-03
origin/backup/m6-lost-cards-2026-03-03
origin/backup/pr-27-2026-03-03
origin/backup/pr-28-2026-03-03
origin/backup/tilt-fix-config-sync-2026-03-03
origin/backup/tmp-36-onto-38-2026-03-03
origin/broken-state-backup
origin/incident/free-pour-zero-balance
origin/infra/syncthing-dev-workflow
origin/master
```

### Open PRs

`gh pr list --state open --json number,title,headRefName,baseRefName,state,mergeable,isDraft,url`

```json
[
  {
    "number": 40,
    "title": "Infra: replace Tilt workflow with Syncthing and stabilize backend URL handling",
    "headRefName": "infra/syncthing-dev-workflow",
    "baseRefName": "master",
    "state": "OPEN",
    "mergeable": "MERGEABLE",
    "isDraft": false,
    "url": "https://github.com/glebkovalerenko-ui/beer-tap-system/pull/40"
  },
  {
    "number": 39,
    "title": "Hotfix: guard free pours with zero balance and document RCA",
    "headRefName": "incident/free-pour-zero-balance",
    "baseRefName": "master",
    "state": "OPEN",
    "mergeable": "MERGEABLE",
    "isDraft": false,
    "url": "https://github.com/glebkovalerenko-ui/beer-tap-system/pull/39"
  }
]
```

### Master integrity

Final verification before this docs commit:

```text
git rev-parse HEAD         = 7630de9622e3a8988c7ede574010be34859a0a65
git rev-parse origin/master = 7630de9622e3a8988c7ede574010be34859a0a65
```

Interpretation:

- `master` was clean and exactly matched `origin/master` before report documentation was added.

### Alembic heads

`python -m alembic heads`

```text
0012_m6_rejected_sync (head)
```

Interpretation:

- alembic graph is clean: exactly one head.

## Recommended Next Actions

1. Review and merge PR #39.
2. Review and merge PR #40.
3. After both merges, delete `incident/free-pour-zero-balance` and `infra/syncthing-dev-workflow`.
4. Keep `origin/backup/*` and `origin/broken-state-backup` until the team explicitly agrees they are no longer needed.
