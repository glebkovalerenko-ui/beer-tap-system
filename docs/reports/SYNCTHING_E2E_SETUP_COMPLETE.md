# Syncthing E2E Setup Complete

Date: 2026-03-03
Branch: `infra/syncthing-dev-workflow`

## IDs

- Windows device ID: `YZN6FOO-3XXDTFQ-I6XHHRV-5U6IWOI-VEFT2VI-7DM5FL6-LJP7UMG-Z7VSJQS`
- Linux device ID: `JHGN2EA-HMRNDKN-LKB5MYQ-T5CTT7X-LOUCG3F-HKPAA6L-V6F77PT-ER7TKA3`
- Folder ID: `beer-tap-system-dev`
- Windows folder path: `C:\Users\CatNip420\Documents\Projects\beer-tap-system`
- Linux folder path: `/home/cybeer/beer-tap-system`

## Tilt Removal

- `where tilt` before cleanup: `C:\Tools\tilt\tilt.exe`
- `Get-Process tilt` before cleanup: one running `tilt` process was present
- Removal result: `yes`
- `where tilt` after cleanup: not found
- `Get-Process tilt -ErrorAction SilentlyContinue` after cleanup: no process
- Removed leftovers:
  - `C:\Tools\tilt\tilt.exe`
  - `%USERPROFILE%\.tilt` not present
  - `%LOCALAPPDATA%\Tilt` not present

## Windows Syncthing Setup

- Installed package: `GermanCoding.SyncTrayzor 2.1.0`
- `where syncthing` after install: not found on PATH
- Effective binary used: `%LOCALAPPDATA%\Programs\SyncTrayzor\syncthing.exe`
- Windows GUI/API address: `127.0.0.1:8384`
- Windows API key was read from local Syncthing config and used for automation

## Pairing

### Windows side

- Added Linux device `cybeer-hub` through Syncthing REST API
- Added folder `beer-tap-system-dev` through Syncthing REST API
- Folder mode on Windows: `sendonly`
- Folder references both devices: Windows + Linux
- Syncthing restart via REST completed successfully

### Linux side

- Linux Syncthing service: `systemd --user`, status `active`
- Linux folder mode: `receiveonly`
- Linux accepted the Windows device by updating Syncthing `config.xml`
- Linux Syncthing service was restarted successfully

### Connection result

- Windows `rest/system/connections` shows Linux connected
- Observed connection:
  - address: `192.168.0.110:22000`
  - type: `tcp-server`
  - clientVersion: `v1.29.5`
  - connected: `true`

## Sync Verification

### Probe create

- Created file: `backend/_syncthing_probe.txt`
- Linux result: file appeared at `/home/cybeer/beer-tap-system/backend/_syncthing_probe.txt`
- Linux content matched Windows content

### Probe delete

- Deleted file on Windows
- Forced folder scan via Windows Syncthing REST
- Linux result: file disappeared from `/home/cybeer/beer-tap-system/backend/_syncthing_probe.txt`

### Folder status after verification

- Windows folder state: `idle`
- `needTotalItems=0`
- `receiveOnlyTotalItems=0`
- Connection remained active during sync test

## Backend Hot Reload Verification

### Preconditions

- Backend container source mount:
  - `/home/cybeer/beer-tap-system/backend:/app`
- Compose source:
  - `/home/cybeer/beer-tap-system/docker-compose.yml`
- Backend service:
  - `beer_backend_api`

### Test

1. Added temporary marker to [`backend/main.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/main.py): `print("SYNCTHING_TEST")`
2. Triggered Windows Syncthing folder scan
3. Observed Linux backend logs:
   - `WARNING: WatchFiles detected changes in 'main.py'. Reloading...`
   - `SYNCTHING_TEST`
4. Removed the temporary marker from [`backend/main.py`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/backend/main.py)
5. Observed another backend reload

### Current backend status

- `curl http://localhost:8000/api/system/status` on Linux returns `{"key":"emergency_stop_enabled","value":"false"}`
- `docker compose -f /home/cybeer/beer-tap-system/docker-compose.yml ps` shows:
  - `beer_backend_api` healthy
  - `beer_postgres_db` healthy

## Admin App Check

- Active code search for `localhost:8000` found no live admin-app fallback path
- `localhost:5173` remains only Tauri frontend `devUrl`
- Active backend URL sources remain:
  - [`admin-app/src/lib/config.js`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/config.js)
  - [`admin-app/src-tauri/src/server_config.rs`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/src/server_config.rs)
- `VITE_API_BASE_URL` in the current Windows shell session: unset
- Recommended dev value: `http://cybeer-hub:8000`

## Final Architecture

```text
Windows IDE / Codex
  |
  | edit files in repo
  v
Syncthing (Send Only)
  |
  | LAN sync, folder id: beer-tap-system-dev
  v
cybeer-hub Syncthing (Receive Only)
  |
  | writes to /home/cybeer/beer-tap-system
  v
docker compose on Linux
  |
  +--> beer_backend_api
  |      bind mount: /home/cybeer/beer-tap-system/backend:/app
  |      uvicorn --reload
  |
  +--> beer_postgres_db
         named volume: beer-tap-system_postgres_data

Windows admin-app -> http://cybeer-hub:8000 -> Linux backend -> Postgres
RPi controller   -> http://cybeer-hub:8000 -> Linux backend -> Postgres
```

## Known Issues

- `where syncthing` on Windows is still empty because SyncTrayzor did not add `syncthing.exe` to PATH.
- The first pairing pass created `sync-conflict-*` files on Linux because the Linux folder had been pre-seeded before Windows became the source of truth.
- Those `sync-conflict-*` files were deleted manually on Linux after pairing.
- Historical docs in `docs/reports/` still contain `localhost:8000` examples for old reports and diagnostics; these are not active runtime config.
- `VITE_API_BASE_URL` is not exported globally in the current Windows shell, so web/Tauri dev should set it explicitly when starting admin-app.

## Rollback

1. Stop using Syncthing folder `beer-tap-system-dev` on Windows and Linux.
2. Disable Linux Syncthing service:
   - `systemctl --user disable --now syncthing`
3. If needed, disable or uninstall SyncTrayzor on Windows.
4. Keep `/home/cybeer/beer-tap-system` as a normal working copy or remove it manually.
5. Keep Docker data intact:
   - do not run `docker compose down -v`
   - do not remove `beer-tap-system_postgres_data`
6. Backend can still be started from `/home/cybeer/beer-tap-system` with:
   - `docker compose up -d --build`

## Verdict

- Pairing: successful
- Sync create/delete: successful
- Backend hot reload: successful
- Tilt removed from Windows: yes
- Verdict: `Dev workflow stabilized`
