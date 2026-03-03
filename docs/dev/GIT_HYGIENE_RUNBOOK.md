# Git Hygiene Runbook

## Goal

Keep `master` clean, keep PRs reviewable, and prevent orphan branches with unpublished work.

## Branch Rules

- Start work from fresh `master`.
- One task = one branch.
- Branch names must reflect intent:
  - `feature/...`
  - `fix/...`
  - `infra/...`
  - `incident/...`
  - `backup/...` only for preservation, never for active delivery
- Do not keep `pr-*` or `tmp-*` branches after the task is resolved.

## PR Rules

- Open a PR as soon as a branch has non-trivial unique commits.
- If a branch is ahead locally and has no PR, either:
  - push and open a PR, or
  - convert it into `backup/<name>-YYYY-MM-DD`
- Closed unmerged PR branches must be either:
  - deleted if patch-equivalent to `master`, or
  - preserved under `backup/*` before deletion

## Cleanup Rules

- After merge, delete the source branch locally and on origin the same day.
- Run regularly:

```text
git fetch --all --prune
git branch -vv
git branch -r
gh pr list --state open
gh pr list --state closed --limit 30
```

- Treat these as danger signals:
  - local branch `ahead` with no push
  - remote branch with no PR
  - closed PR whose source branch still exists
  - stale helper branches like `pr-*`, `tmp-*`
  - multiple milestone branches that clearly supersede each other

## Safe Deletion Policy

- Delete immediately only when one of these is true:
  - branch PR is merged
  - branch is patch-equivalent to `master`
  - branch is fully contained in another kept branch
- If not true, preserve first:

```text
git branch -f backup/<branch>-YYYY-MM-DD <source>
git push -u origin backup/<branch>-YYYY-MM-DD
```

## Rebase and Force-Push Policy

- Rebase active branches onto current `master` before merge when practical.
- If a PR branch was rebased, update it only with:

```text
git push --force-with-lease origin <branch>
```

- Never use plain `--force` when `--force-with-lease` is enough.

## AI Agent Completion Checklist

- Verify current branch and `master`.
- Run `git fetch --all --prune`.
- Check local/remote divergence with `git branch -vv`.
- Check open and recently closed PRs with `gh`.
- Preserve unique stale work with `backup/*` before deletion.
- Delete merged and obsolete branches on both local and origin.
- Ensure active PRs are `MERGEABLE`.
- Run repo-specific safety checks:
  - `python -m alembic heads`
- Leave a written report in `docs/reports/`.

## Expected End State

- `master` matches `origin/master`.
- Only active work branches remain outside `backup/*`.
- Open PR list contains only real work in progress.
- Stale history exists only under explicit `backup/*` names.
