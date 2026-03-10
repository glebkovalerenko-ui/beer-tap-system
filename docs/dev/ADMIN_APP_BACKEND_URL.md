# Admin App Backend URL in Development

Read this after `README.md` and `docs/architecture/SYSTEM_ARCHITECTURE_V1.md`.

## What is the backend URL

- Web/dev mode uses `VITE_API_BASE_URL` or `VITE_BACKEND_BASE_URL`.
- Tauri desktop mode uses the persisted runtime setting, with packaged default `http://cybeer-hub:8000`.
- `localhost:5173` is only the Vite frontend dev server.

## What is not the backend URL

- `devUrl=http://localhost:5173` in `admin-app/src-tauri/tauri.conf.json` is not a backend endpoint.
- There is no active fallback from frontend or Tauri to `http://localhost:8000` unless explicitly configured.

## Recommended Windows dev setup

### Web/dev

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
cd admin-app
npm run dev
```

### Tauri dev

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
cd admin-app
npm run tauri dev
```

## Runtime persistence model

- build-time environment config seeds the app in web/dev
- Tauri runtime config persists the desktop backend URL in app config storage
- connection testing uses `/api/system/status`

## Source of truth in code

- `admin-app/src/lib/config.js`
- `admin-app/src-tauri/src/server_config.rs`
