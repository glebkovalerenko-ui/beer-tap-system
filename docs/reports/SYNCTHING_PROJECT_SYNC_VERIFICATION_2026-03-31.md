# Syncthing Project Sync Verification (2026-03-31)

## 1. Scope

This pass did four things together:

- committed and pushed the current Windows working tree on branch `feature/guest-visit-card-consolidation-sprint1`
- preserved the recent visit recovery and lost-card workflow changes
- preserved the new dev cleanup tooling and hub reconcile units
- verified that `cybeer-hub` (`192.168.0.110`) and `cybeer-00` (`192.168.0.114`) received the current project files through Syncthing

The pushed commit is:

- `e17730722621081b6ce95674087b4def62470b0b` - `Implement visit recovery flow and sync tooling`

## 2. Local Pre-Push Verification

Before push, the current tree was verified locally:

- `python -m pytest backend/tests/test_visit_invariants.py backend/tests/test_m6_lost_cards.py backend/tests/test_operator_api.py -q`
  - result: `34 passed`
- `npm run build` in `admin-app`
  - result: success
- `node admin-app/scripts/navigation_ia_smoke.mjs`
  - result: all checks `OK`

The local branch head after commit and push is:

- branch: `feature/guest-visit-card-consolidation-sprint1`
- head: `e17730722621081b6ce95674087b4def62470b0b`

## 3. Delivered Change Set

The synced working tree now includes the current operator and infrastructure work:

- blocked-lost visit recovery in the real `#/visits` workspace
- visit-scoped `restore-lost-card` / cancel-lost flow
- reissue flow that can auto-register a brand-new card UID
- normal visit open that can auto-register an unknown card into the pool
- dev DB cleanup tooling:
  - [backend/dev_db_cleanup.py](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/dev_db_cleanup.py)
  - [scripts/dev_db_cleanup.ps1](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/scripts/dev_db_cleanup.ps1)
  - [scripts/dev_db_cleanup.sh](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/scripts/dev_db_cleanup.sh)
- hub reconcile deployment files:
  - [deploy/hub/beer-tap-sync-reconcile.sh](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/deploy/hub/beer-tap-sync-reconcile.sh)
  - [deploy/hub/beer-tap-sync-reconcile.service](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/deploy/hub/beer-tap-sync-reconcile.service)
  - [deploy/hub/beer-tap-sync-reconcile.timer](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/deploy/hub/beer-tap-sync-reconcile.timer)
  - [deploy/hub/beer-tap-system.service](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/deploy/hub/beer-tap-system.service)

## 4. Live Syncthing Verification

### cybeer-hub (`cybeer@192.168.0.110`)

Observed over SSH on `2026-03-31`:

- `systemctl --user is-active syncthing` -> `active`
- `systemctl is-active beer-tap-system.service` -> `active`
- `systemctl is-active beer-tap-sync-reconcile.timer` -> `active`
- Syncthing `db/status` for folder `beer-tap-system-dev`:
  - `state=idle`
  - `errors=0`
  - `pullErrors=0`
  - `needTotalItems=0`
  - `receiveOnlyTotalItems=0`
- Syncthing `db/localchanged` -> empty

Repo-path file hashes on hub match the local Windows checkout:

- `3260639f97db5b221b59fce483851b97457861a6f38db3d723ecff5de8c88b93` - `backend/crud/visit_crud.py`
- `42637554206ba3c81ada044deb03f62ceff6ecf605c6bda7c2e64e2a4396d3ce` - `backend/api/visits.py`
- `7a6a62f6e8c0736bc52dd7c0541166fa5c06ad785b7ed88098ab20d7da533c8a` - `admin-app/src/routes/Visits.svelte`
- `ab6c8f2b934cf85cbc34fa513d0d25efa7a05b7613749ec8bfdf431b14a1cc9c` - `backend/dev_db_cleanup.py`
- `baf1e8347ec4762cb7c5f89763d1b37646e18b4fc203c280f1227743c561a90f` - `deploy/hub/beer-tap-sync-reconcile.sh`

Runtime confirmation on hub:

- `docker ps` shows `beer_backend_api` healthy
- `docker ps` shows `beer_postgres_db` healthy
- hashes inside container `beer_backend_api` match the synced repo for:
  - `/app/crud/visit_crud.py`
  - `/app/api/visits.py`
  - `/app/dev_db_cleanup.py`

### cybeer-00 (`cybeer@192.168.0.114`)

Observed over SSH on `2026-03-31`:

- `systemctl --user is-active syncthing` -> `active`
- Syncthing `db/status` for folder `beer-tap-system-dev`:
  - `state=idle`
  - `errors=0`
  - `pullErrors=0`
  - `needTotalItems=0`
  - `receiveOnlyTotalItems=0`
- Syncthing `db/localchanged` -> empty

Repo-path file hashes on controller match the local Windows checkout:

- `3260639f97db5b221b59fce483851b97457861a6f38db3d723ecff5de8c88b93` - `backend/crud/visit_crud.py`
- `42637554206ba3c81ada044deb03f62ceff6ecf605c6bda7c2e64e2a4396d3ce` - `backend/api/visits.py`
- `7a6a62f6e8c0736bc52dd7c0541166fa5c06ad785b7ed88098ab20d7da533c8a` - `admin-app/src/routes/Visits.svelte`
- `ab6c8f2b934cf85cbc34fa513d0d25efa7a05b7613749ec8bfdf431b14a1cc9c` - `backend/dev_db_cleanup.py`
- `baf1e8347ec4762cb7c5f89763d1b37646e18b4fc203c280f1227743c561a90f` - `deploy/hub/beer-tap-sync-reconcile.sh`

Controller runtime observation:

- `systemctl is-active beer-tap-controller.service` -> `active`
- `systemctl is-active tap-display-agent.service` -> `active`

## 5. Important Boundary

Both receive-only Linux nodes still report Git `HEAD` as:

- branch: `investigation/processing-sync-stuck`
- head: `c7718cca86fecc604fc89c1a0647606a18196383`

That does not mean Syncthing is stale.

It means the receive-only repo paths are being updated as working trees, not as Git checkouts. In this topology, Syncthing delivers file bytes and deletions, but it does not advance Git refs or clean the remote Git index automatically.

For the current verification target, the source of truth is:

- Syncthing `db/status` and `db/localchanged`
- matching SHA-256 hashes of selected files
- matching runtime files inside the backend container on `cybeer-hub`

If Git ref parity on the Linux nodes is needed later, that should be handled as a separate controlled repo-normalization step, not mixed into the receive-only Syncthing workflow.

## 6. Verdict

`e17730722621081b6ce95674087b4def62470b0b` is pushed to `origin`, and the current project working tree is confirmed present on both `cybeer-hub` and `cybeer-00` through Syncthing.
