# Syncthing Backend Desync RCA And Fix (2026-03-25)

## Summary

On `2026-03-25` the backend on `192.168.0.110:8000` was serving an outdated working tree. The visible symptom in Admin App was that logging in as `admin / fake_password` still resolved to the fallback `operator` role.

The underlying issue was not frontend auth logic. The hub backend was stale and did not include role-aware token claims or `/api/me`.

## Symptoms

- `POST /api/token` on `192.168.0.110:8000` returned a JWT without `role` and `permissions`.
- `GET /api/me` returned `404`.
- Admin App fell back to `operator` because JWT claims had no role.
- Hub Syncthing folder was not current even though the service itself was running.

## Root Cause

The desync had multiple contributing causes:

1. Windows Syncthing sender was not running.
   - Local SyncTrayzor/Syncthing on the workstation had been stopped.
   - Hub stayed on the last received snapshot until the workstation sender came back.

2. Runtime media files were written into the Syncthing-managed repo tree.
   - Backend uploaded media landed under `backend/storage/media-assets`.
   - Those files were created as `root:root` with restrictive permissions.
   - Hub Syncthing scanner reported `permission denied` on those files and accumulated stale local folder drift.

3. Ignore pattern drift on the receive-only node.
   - `.stignore` must be applied on each Syncthing node.
   - The hub copy did not yet include the `backend/storage/` ignore rule, so Syncthing kept indexing a runtime directory that should never have been part of the shared working tree.

4. The first storage isolation attempt was not robust enough.
   - Mounting a named volume under `/app/storage/media-assets` while `/app` itself was a bind mount proved unreliable in this setup.
   - The durable fix was to move media storage completely outside the bind-mounted tree.

## Fix Applied

### Workstation

- Started local Syncthing again from the existing SyncTrayzor installation.
- Added Windows startup shortcut:
  - `C:\Users\CatNip420\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SyncTrayzor.lnk`

### Repository

- Added `backend/storage/` to [`.stignore`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.stignore).
- Added `backend/storage/` to [`.gitignore`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.gitignore).
- Updated [docker-compose.yml](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docker-compose.yml):
  - kept backend code bind-mounted at `/app`
  - mounted `backend_media_assets` volume at `/srv/beer-media-assets`
  - set `MEDIA_STORAGE_ROOT=/srv/beer-media-assets`
- Updated [docs/dev/SYNCTHING_DEV_RUNBOOK.md](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/docs/dev/SYNCTHING_DEV_RUNBOOK.md) to document the runtime-data boundary.
- Added optional `MEDIA_STORAGE_ROOT` note to [`.env.example`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/.env.example).

### Hub (`192.168.0.110`)

- Reconnected workstation sender to hub Syncthing peer.
- Manually deployed updated `.stignore` onto the hub node.
- Recreated `beer_backend_api` with the updated compose config.
- Restored existing media assets into the new external storage volume at `/srv/beer-media-assets`.
- Removed stale Syncthing drift on the receive-only node and forced `revert` + `scan`.

## Verification

### Syncthing

- Hub folder `beer-tap-system-dev` reached:
  - `errors: 0`
  - `pullErrors: 0`
  - `receiveOnlyTotalItems: 0`
  - `state: idle`
- Workstation and hub reconnected successfully.

### Backend auth

- `POST /api/token` now returns JWT with:
  - `role=engineer_owner`
  - `permissions=[...]`
- `GET /api/me` now returns:
  - `username=admin`
  - `role=engineer_owner`

### Media assets

All four restored media assets return `200 OK` from `GET /api/media-assets/{asset_id}/content` with the display token:

- `279a5fa4-eabb-4218-aa51-186b9b352727`
- `e6e4173b-51b4-4f38-936e-54abe08a2248`
- `0af7eca2-bd87-4a13-aca4-82e87d17259f`
- `4c990d9d-e4fd-47c8-b356-6da3330ca23b`

## Operational Rule Going Forward

- Windows remains the single writer for the repo checkout.
- Linux hub remains `Receive Only`.
- Runtime-generated backend files must never be stored inside the Syncthing-managed repo tree.
- If `.stignore` changes, apply it on each Syncthing node explicitly; do not assume the ignore file itself will safely propagate operational state.
- If the workstation sender is offline, the hub will not advance to new code even if its Syncthing service is healthy.
