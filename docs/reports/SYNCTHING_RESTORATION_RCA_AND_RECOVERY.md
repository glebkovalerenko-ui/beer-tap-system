# Syncthing Restoration RCA And Recovery

## 1. Problem statement

The development Syncthing workflow for `beer-tap-system` had stopped being trustworthy.

Observed impact before recovery:

- Windows, Raspberry Pi controller, and hub were still partially connected, but the folder state was no longer converging predictably.
- The Windows node looked superficially healthy (`idle`), but the Linux nodes were not actually reaching a clean in-sync state.
- Pi and hub development copies had drifted away from the canonical Windows checkout.
- Runtime/build artifacts had entered the live Syncthing index.
- hub had filesystem-level failures that blocked file application.

The goal of this recovery was to restore a safe development topology in which Windows is the only canonical writer and Pi/hub are predictable receive-only replicas.

## 2. Topology and current setup

### Devices

- Windows development machine: `YZN6FOO-3XXDTFQ-I6XHHRV-5U6IWOI-VEFT2VI-7DM5FL6-LJP7UMG-Z7VSJQS`
- Raspberry Pi controller: `NODMOBU-AYSFELD-Y7MGYII-WNK4PPK-VWKZ4MZ-ONATZYN-YWELRZZ-7KDXLAI`
- cybeer-hub: `JHGN2EA-HMRNDKN-LKB5MYQ-T5CTT7X-LOUCG3F-HKPAA6L-V6F77PT-ER7TKA3`

### Shared folder

- Folder ID: `beer-tap-system-dev`
- Windows path: `C:\Users\CatNip420\Documents\Projects\beer-tap-system`
- Pi path: `/home/cybeer/beer-tap-system`
- hub path: `/home/cybeer/beer-tap-system`

### Service mode

- Windows: SyncTrayzor-managed Syncthing process
- Pi: `systemd --user` service `syncthing.service`
- hub: `systemd --user` service `syncthing.service`

### Folder role before recovery

- Windows: `sendreceive`
- Pi: `sendreceive`
- hub: `receiveonly`

### Folder role after recovery

- Windows: `sendonly`
- Pi: `receiveonly`
- hub: `receiveonly`

## 3. Audit findings

### Service and topology findings

- Both Linux user services existed and were able to run, so the failure was not caused by Syncthing simply being offline.
- The live topology had drifted away from the documented one-writer model. Pi was configured as a writer (`sendreceive`) even though the intended workflow was Windows -> Linux replicas.
- Linux repositories were on different branches and commits from the Windows development checkout.

### Pre-recovery Windows health snapshot

- Canonical Windows branch: `investigation/processing-sync-stuck`
- Canonical Windows commit: `c7718cca86fecc604fc89c1a0647606a18196383`
- Windows folder type: `sendreceive`
- `db/status`: `state=idle`, `errors=2`, `pullErrors=2`, `needTotalItems=2`, `needDeletes=2`
- Pre-recovery completion from Windows:
  - Pi: `completion=99.97475120575614`, `needItems=10`, `needBytes=11853`
  - hub: `completion=5.415330629903847`, `needItems=2082`, `needBytes=44402599`

### Pre-recovery Pi findings

- Syncthing folder type: `sendreceive`
- Repo branch/commit:
  - branch: `hotfix/tap-display-kiosk-reboot`
  - commit: `a93f4a72763d55ce01e7a7e83a7561732a9133d5`
- Local drift captured before alignment:
  - modified: `tap-display-client/src/App.svelte`
  - untracked: `docs/reports/TAP_DISPLAY_PROCESSING_SYNC_RCA.md`

### Pre-recovery hub findings

- Syncthing folder type: `receiveonly`
- Repo branch/commit:
  - branch: `feature/tap-display-real-pi-bringup`
  - commit: `3256c6cd0c232ead70cc1779f1bea5de10b07201`
- `/home/cybeer/beer-tap-system/.stfolder` was missing.
- Large parts of the repo tree under `backend/` were not safely writable by `cybeer`.
- Audit captured many permission failures such as:
  - `chmod ... operation not permitted` on `backend/.pytest_cache` and `__pycache__`
  - `open ... .syncthing.*.tmp: permission denied` across `backend/alembic`, `backend/api`, `backend/crud`, and `backend/tests`
- Audit also captured non-`cybeer:cybeer` ownership under the synced repo, especially under Python cache directories.

### Live-index pollution findings

- The live Syncthing index contained runtime/build artifacts that do not belong in the shared repo workflow.
- Required ignore coverage was missing for:
  - `.venv-controller/`
  - `admin-app/.svelte-kit/`
  - `rpi-controller/local_journal.db`
  - `rpi-controller/local_journal.db-wal`
  - `rpi-controller/local_journal.db-shm`
  - `tap-display-agent/cache/`
- Windows also had delete blockers for ignored cache directories:
  - `.pytest_cache`
  - `backend/.pytest_cache`

## 4. Root cause

### Main root cause

Syncthing stopped being reliable because the folder topology drifted from a single-writer model into a multi-writer model, while the hub copy simultaneously became filesystem-unsafe for Syncthing to write into.

In practice this meant:

- Windows was no longer authoritative because it was left in `sendreceive` mode.
- Pi was allowed to publish local repo/runtime state back into the cluster because it was also `sendreceive`.
- hub could not apply a large part of the shared index because its repo path had a missing marker directory, ownership drift, and permission-denied failures.

### Contributing factors

- Incomplete ignore policy allowed runtime/build artifacts to enter the index.
- A stale `.venv-controller` subtree still existed on Windows and had to be removed explicitly.
- Linux repos were on different branches and commits than the canonical Windows checkout.
- `.stignore` needed to be deployed locally on Pi and hub; updating it on Windows alone was not sufficient.

## 5. Recovery actions

### Backup and freeze

- Created timestamped backup roots before destructive normalization:
  - Windows: `C:\Users\CatNip420\Documents\syncthing-restoration-backup-20260316-222644`
  - Pi: `/home/cybeer/syncthing-restoration-backup-20260316-222644`
  - hub: `/home/cybeer/syncthing-restoration-backup-20260316-222644`
- Captured Syncthing config/state snapshots, connections, folder status, errors, and Git state on all three nodes.
- Stopped Syncthing on Pi and hub during backup and normalization.

### Drift capture before Git alignment

- Pi backup captured:
  - `git status`
  - `git diff`
  - untracked file list
  - copies of local drift files and runtime state
- hub backup captured:
  - `git status`
  - `git diff`
  - non-`cybeer` path inventory
  - copies of non-`cybeer` files under the synced repo

### hub filesystem repair

- Recreated `/home/cybeer/beer-tap-system/.stfolder`
- Restored repo ownership to `cybeer:cybeer`
- Restored repo writability with safe `u+rwX`
- Removed backed-up ephemeral blockers:
  - `backend/.pytest_cache`
  - Python `__pycache__` directories under the previously failing paths
  - stale `.syncthing.*.tmp` files

### Git normalization

- Fixed canonical source to the Windows checkout on:
  - branch: `investigation/processing-sync-stuck`
  - commit: `c7718cca86fecc604fc89c1a0647606a18196383`
- After backup completion, aligned both Linux repos to that exact commit.
- No repo was recloned and `.git` was preserved.

### Syncthing topology normalization

- Changed Windows folder `beer-tap-system-dev` to `sendonly`
- Changed Pi folder `beer-tap-system-dev` to `receiveonly`
- Kept hub folder `beer-tap-system-dev` as `receiveonly`
- Kept Windows as the only canonical writer

### Ignore policy and stale-index cleanup

- Expanded `.stignore` on Windows to exclude runtime/build artifacts that had polluted the live index.
- Deployed the final `.stignore` locally to Pi and hub so the ignore policy matched on every node.
- Removed stale Windows-side runtime/cache artifacts that had to leave the cluster index:
  - `.venv-controller/`
  - `.pytest_cache/`
  - `backend/.pytest_cache/`
- Confirmed before final override/revert that the live index no longer contained matches for:
  - `.venv-controller`
  - `admin-app/.svelte-kit`
  - `rpi-controller/local_journal.db*`
  - `tap-display-agent/cache`

### Final reconcile

- Ran Windows `send-only override`
- Ran `receive-only revert` on Pi
- Ran `receive-only revert` on hub

## 6. Drift/conflict handling

### Canonical source

- Canonical source of truth: Windows checkout
- Canonical branch: `investigation/processing-sync-stuck`
- Canonical commit: `c7718cca86fecc604fc89c1a0647606a18196383`

### Saved drift and conflict artifacts

- Pi drift backup root:
  - `/home/cybeer/syncthing-restoration-backup-20260316-222644/pi`
- hub drift backup root:
  - `/home/cybeer/syncthing-restoration-backup-20260316-222644/hub`
- Post-override conflict safety backup on hub:
  - `/home/cybeer/syncthing-restoration-backup-20260316-222644/hub/post-override-conflicts`

### Recovery safety notes

- No repo was deleted.
- No `.git` directory was deleted.
- Linux branch alignment was only done after external backup of local drift.
- Conflict cleanup was not done blindly; conflict artifacts were backed up first.

## 7. Post-recovery verification

### Ignore-rule proof before override/revert

Windows live-index checks were repeated after ignore rollout and cleanup.

Results before final override/revert:

- `HUB_MATCH_COUNT=0`
- `PI_MATCH_COUNT=0`
- `LOCAL_NEED_MATCH_COUNT=0`

That proved the targeted runtime/build artifacts were no longer present in the live Syncthing index.

### Real sync tests

#### Windows -> Pi and hub

- Created `backend/_syncthing_restore_probe.txt` on Windows.
- Confirmed the file appeared on Pi and hub with exact content:
  - `probe-step-1 2026-03-16T22:48:30+03:00`
- Updated the same file on Windows.
- Confirmed the updated content arrived on Pi and hub exactly:
  - `probe-step-2 2026-03-16T22:53:45+03:00`
- Deleted the probe on Windows.
- Confirmed the file was deleted on Pi and hub.

#### Tracked-file propagation

- Added a temporary marker line to `README.md` on Windows.
- Confirmed the exact marker line arrived on Pi and hub.
- Removed the marker afterward so the repo content returned to normal.

#### Reverse receive-only safety check

- Created `backend/_syncthing_reverse_local.txt` locally on Pi.
- Confirmed it did not appear on Windows.
- Confirmed it did not appear on hub.
- Pi exposed it only as local receive-only drift.
- Removed the file on Pi and returned the folder to clean `idle` state.

### Final health snapshot

Final metrics were captured after the report and final file-state cleanup were synchronized.

Service health:

- Pi:
  - `systemctl --user is-active syncthing` -> `active`
  - `systemctl --user is-enabled syncthing` -> `enabled`
  - `loginctl show-user cybeer -p Linger` -> `Linger=yes`
- hub:
  - `systemctl --user is-active syncthing` -> `active`
  - `systemctl --user is-enabled syncthing` -> `enabled`
  - `loginctl show-user cybeer -p Linger` -> `Linger=yes`

Final folder-role confirmation:

- Windows: `sendonly`
- Pi: `receiveonly`
- hub: `receiveonly`

Final `.stignore` deployment confirmation:

- Windows SHA256: `bbf1b735130e2bdddcfeb35e7b858037155c3bbef68d2072ac8af2b05158943b`
- Pi SHA256: `bbf1b735130e2bdddcfeb35e7b858037155c3bbef68d2072ac8af2b05158943b`
- hub SHA256: `bbf1b735130e2bdddcfeb35e7b858037155c3bbef68d2072ac8af2b05158943b`

Final Syncthing health:

- Windows `db/status`:
  - `state=idle`
  - `errors=0`
  - `pullErrors=0`
  - `needTotalItems=0`
  - `needDeletes=0`
  - `globalFiles=1513`
  - `globalDirectories=356`
  - `globalDeleted=296`
  - `globalBytes=42231965`
- Windows completion:
  - Pi: `completion=100`, `needItems=0`, `needBytes=0`, `remoteState=valid`
  - hub: `completion=100`, `needItems=4`, `needBytes=0`, `remoteState=valid`
- Pi `db/status`:
  - `state=idle`
  - `errors=0`
  - `pullErrors=0`
  - `needTotalItems=0`
  - `receiveOnlyTotalItems=0`
- hub `db/status`:
  - `state=idle`
  - `errors=0`
  - `pullErrors=0`
  - `needTotalItems=0`
  - `receiveOnlyTotalItems=0`

Final repo safety confirmation:

- Pi branch/commit:
  - branch: `investigation/processing-sync-stuck`
  - commit: `c7718cca86fecc604fc89c1a0647606a18196383`
- hub branch/commit:
  - branch: `investigation/processing-sync-stuck`
  - commit: `c7718cca86fecc604fc89c1a0647606a18196383`
- `.git` remained intact on all nodes.
- The synced recovery report itself is present on Pi and hub.
- The temporary `README.md` verification marker was confirmed removed again on Pi and hub.

## 8. Remaining limitations

- `.stignore` is effectively local Syncthing control state and had to be deployed on Pi and hub explicitly; editing it on Windows alone did not propagate it as ordinary project data.
- Windows `db/completion` for hub still reports `needItems=4` while also reporting `completion=100`. Those four items are stale symlink entries under `.venv-display-agent`:
  - `.venv-display-agent/bin/python`
  - `.venv-display-agent/bin/python3`
  - `.venv-display-agent/bin/python3.13`
  - `.venv-display-agent/lib64`
- hub itself is clean (`state=idle`, `needTotalItems=0`, `receiveOnlyTotalItems=0`, no folder errors), so this is a non-blocking metadata tail rather than a live sync failure. Removing or relocating `.venv-display-agent` outside the synced repo would be the clean follow-up if a strict `needItems=0` completion view is required.
- Syncing a Git working tree across Windows and Linux still carries a general cross-OS line-ending risk. That risk is reduced by the restored one-writer topology, but it is not eliminated by Syncthing itself.
- Pi and hub Git working trees still show `tap-display-client/src/App.svelte` as modified even though Syncthing reports them in sync. This is consistent with the cross-OS working-tree normalization risk above, not with a current Syncthing transport failure.
- Windows Syncthing is managed through SyncTrayzor rather than `systemd`, so restart behavior is different from the Linux nodes.

## 9. Final verdict

`RESTORED, BUT SMALL FOLLOW-UP NEEDED`
