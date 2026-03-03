# Admin App Backend URL In Dev

## What matters

- Backend base URL for web/dev comes from `VITE_API_BASE_URL` or `VITE_BACKEND_BASE_URL`.
- Backend base URL for Tauri desktop comes from the persisted runtime setting, with packaged default `http://cybeer-hub:8000`.
- `localhost:5173` in `admin-app/src-tauri/tauri.conf.json` is only the Vite frontend dev server for Tauri.

## What does not matter

- `devUrl=http://localhost:5173` is not a backend endpoint.
- There is no active frontend or Tauri fallback to `http://localhost:8000`.

## Recommended dev settings on Windows

PowerShell:

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
cd admin-app
npm run dev
```

For Tauri dev:

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
cd admin-app
npm run tauri dev
```

## Source of truth in code

- Web/dev resolver: [`admin-app/src/lib/config.js`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src/lib/config.js)
- Tauri runtime config: [`admin-app/src-tauri/src/server_config.rs`](/c:/Users/CatNip420/Documents/Projects/beer-tap-system/admin-app/src-tauri/src/server_config.rs)
