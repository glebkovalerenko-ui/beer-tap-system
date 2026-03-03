# Admin App Server URL Configuration

## Current problems (before)

- Backend base URL was split between web build-time config and Tauri runtime state.
- Tauri kept the URL only in process memory, so any server change required restart plus frontend re-bridge, and was not persisted across launches.
- Login HTTP fallback in the frontend used the frontend-resolved URL, while the rest of the desktop app used Rust-side `api_client`, creating two sources of truth.
- Several docs and runbooks still mention `localhost` or older host examples, which increases operator error during rollout.
- There was no user-facing recovery flow for a wrong backend URL other than code/env edits.

## Inventory summary

| File | What it sets | When used | Risk / why it was bad |
| --- | --- | --- | --- |
| `admin-app/src/lib/config.js` | Web/build-time base URL resolution from `VITE_API_BASE_URL` / `VITE_BACKEND_BASE_URL` / `window.__APP_CONFIG__` | Web build, login HTTP fallback, diagnostics | Build-time config only; not persistent for Tauri users. |
| `admin-app/src-tauri/src/api_client.rs` | Rust backend base URL for all Tauri commands | Desktop runtime | Separate from frontend config; value was in memory only. |
| `admin-app/src-tauri/tauri.conf.json` | `devUrl=http://localhost:5173` for Tauri dev frontend | Local Tauri dev only | Not a backend URL, but easy to confuse with backend host settings. |
| `rpi-controller/config.py` | `SERVER_URL` default and env override | Controller runtime | Separate config domain from admin-app; valid for controller, but proves host config is decentralized repo-wide. |
| `docs/dev/TILT_RUNBOOK.md` | `cybeer-hub:8000` as expected backend target | Dev/Tilt runbook | Correct for current topology, but doc-driven config rather than app-level runtime settings. |
| `docs/API_REFERENCE.md`, `docs/QA_Checklist.md`, `docs/baseline.md`, `docs/planning/DECOMPOSITION/*`, `docs/openapi_fragment.yaml` | Various `localhost` examples | Docs, QA, planning | Misleading for pilot operators; easy to cargo-cult stale hostnames. |
| `docs/RPI_INTERNALS.md` | Static IP backend example | Legacy controller doc | Conflicts with `cybeer-hub` default and encourages hardcoded endpoints. |

## New design

### Runtime config (Tauri desktop)

- Single source of truth: `ServerConfig { base_url }`.
- Persistent file: `server-config.json` in Tauri `app_config_dir`.
- Current packaged default: `http://cybeer-hub:8000`.
- Tauri commands:
  - `get_server_base_url`
  - `set_server_base_url`
  - `test_server_connection`
- On startup, Tauri loads the persisted file once and applies it to the Rust HTTP client before UI actions start.
- No production fallback to `localhost`.

### Build/dev config

- Web/dev still resolves the backend from `VITE_API_BASE_URL` or `VITE_BACKEND_BASE_URL`.
- If Tauri runtime commands are unavailable, the frontend stays in build/dev mode and explicitly tells the user to use env config instead of pretending runtime persistence exists.

## Runtime file locations

- Windows: `%APPDATA%\com.beertapsystem.admin\server-config.json`
- Linux: `~/.config/com.beertapsystem.admin/server-config.json`
- macOS: `~/Library/Application Support/com.beertapsystem.admin/server-config.json`

## Validation rules

- Trim whitespace.
- Strip trailing slash.
- Reject empty value.
- Allow only `http://` and `https://`.
- Require a host.

Validation is enforced in both frontend and Rust backend commands.

## Test connection

- Desktop settings call `test_server_connection`.
- Probe endpoint: `GET /api/system/status`.
- The command fails loudly on network errors and on non-2xx HTTP responses.

## How to use

1. Open the admin app.
2. Open `Настройки сервера` from the login screen or the top bar.
3. Enter the backend base URL, for example `http://cybeer-hub:8000`.
4. Click `Проверить соединение`.
5. Click `Сохранить`.

The current effective URL is shown in the modal.

## Operator notes

- In web/dev, the effective backend URL comes from `VITE_API_BASE_URL` or `VITE_BACKEND_BASE_URL`.
- In Tauri desktop, the effective backend URL comes from the persisted runtime file `server-config.json`.
- Operators change the runtime URL through the `Настройки сервера` modal on the login screen or in the top bar.
- UX rule: the `Настройки сервера` button only opens the modal and never triggers login.
- Saving an unreachable or otherwise wrong URL is allowed on purpose so the operator can recover later without rebuilding the app.

## Recovery from wrong URL

If the saved URL is reachable but wrong, or unreachable:

1. Launch the app normally.
2. Open `Настройки сервера`.
3. Enter a working URL.
4. Test and save it.

If the config file itself is corrupted, delete the file manually and restart:

- Windows: `%APPDATA%\com.beertapsystem.admin\server-config.json`
- Linux: `~/.config/com.beertapsystem.admin/server-config.json`
- macOS: `~/Library/Application Support/com.beertapsystem.admin/server-config.json`

After file removal, the app falls back to the packaged default `http://cybeer-hub:8000`.

## How to test

### Build checks

```powershell
cd admin-app
npm run build

cd src-tauri
cargo check
```

### Manual smoke

1. Start the desktop app with a working backend.
2. Enter valid credentials, click `Настройки сервера`, and verify only the modal opens with no login attempt.
3. Click `Войти` and verify login still succeeds.
4. Repeat the `Настройки сервера` click with invalid credentials or an unavailable backend and verify behavior does not change.
5. Open server settings, set a working URL, test, save, and verify normal API operations still work.
6. Change the URL to an unreachable host, save it, restart the app, and verify:
   - UI still opens.
   - Login/settings screen still opens.
   - Connection-related actions show explicit errors.
   - The URL can be corrected without rebuild.

## Files changed by this implementation

- `admin-app/src-tauri/src/server_config.rs`
- `admin-app/src-tauri/src/api_client.rs`
- `admin-app/src-tauri/src/main.rs`
- `admin-app/src/lib/config.js`
- `admin-app/src/lib/api.js`
- `admin-app/src/components/system/ServerSettingsModal.svelte`
- `admin-app/src/components/shell/ShellTopBar.svelte`
- `admin-app/src/routes/Login.svelte`
- `admin-app/src/routes/Dashboard.svelte`
- `docs/reports/ADMIN_APP_SERVER_URL_CONFIG.md`
