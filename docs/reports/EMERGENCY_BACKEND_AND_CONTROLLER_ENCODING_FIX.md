## 1. Symptoms

- Backend on Linux was unreachable from the controller and from the host itself:
  - `Connection refused`
  - `http://192.168.0.110:8000/api/system/status`
- Controller startup logs were reported with mojibake in Russian operator strings.

## 2. Root causes

### Backend

- `beer_backend_api` was not staying healthy even though Docker kept recreating it.
- `docker compose ps` showed the service restarting.
- `docker logs beer_backend_api --tail 200` showed the repeated startup failure:
  - `exec ./entrypoint.sh: no such file or directory`
- On Linux, `/opt/beer-tap-system/backend/entrypoint.sh` had CRLF line endings:
  - `#!/bin/sh^M`
- Because the container entrypoint could not be executed, `uvicorn` never reached the steady state, so nothing served `0.0.0.0:8000` and every `curl` to `127.0.0.1:8000` and `192.168.0.110:8000` failed.

### Controller encoding

- The current localized controller sources in the hotfix branch are valid UTF-8:
  - `main.py`, `flow_manager.py`, `sync_manager.py`, `display_formatters.py`, `terminal_progress.py` all report `charset=utf-8` on Linux.
- `python scripts/encoding_guard.py --all` is clean.
- Linux locale in verification was already UTF-8:
  - `LANG=en_GB.UTF-8`
  - `LC_ALL=` (unset)
- That means the active regression was not broken repository bytes in the current controller files.
- The controller output still depended on the runtime encoding of `stdout`/`stderr`. To make Russian logs deterministic across Linux sessions, controller startup now reconfigures both streams to UTF-8 before logging is initialized.

## 3. What was fixed

- Converted `backend/entrypoint.sh` to LF.
- Added `.gitattributes` rule `*.sh text eol=lf` to stop future Windows checkouts from reintroducing CRLF into shell entrypoints.
- Updated `rpi-controller/main.py` to force UTF-8 on `stdout` and `stderr` before `logging.basicConfig(...)`.

## 4. Files changed

- `.gitattributes`
- `backend/entrypoint.sh`
- `rpi-controller/main.py`

## 5. Verification results

### Backend on Linux

- `docker compose ps`
  - `beer_backend_api` is `Up`
  - published port is `0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp`
- `ss -lntp | grep 8000`
  - listener present on `0.0.0.0:8000` and `[::]:8000`
- `docker logs beer_backend_api --tail 50`
  - entrypoint runs
  - Alembic runs
  - startup check passes
  - Uvicorn starts on `http://0.0.0.0:8000`
- `curl http://127.0.0.1:8000/`
  - `200 OK`
  - `{"Status":"Beer Tap System Backend is running!"}`
- `curl http://127.0.0.1:8000/api/system/status`
  - `200 OK`
  - `{"key":"emergency_stop_enabled","value":"false"}`
- `curl http://192.168.0.110:8000/api/system/status`
  - `200 OK`
  - `{"key":"emergency_stop_enabled","value":"false"}`

### Controller on Linux

- Temporary verification checkout created from the hotfix branch at `/tmp/beer-hotfix-check/rpi-controller`.
- `file -i` on Linux:
  - `main.py`, `flow_manager.py`, `sync_manager.py`, `display_formatters.py`, `terminal_progress.py` all report UTF-8.
- `python3 -c` formatting check:
  - `Налив: 250 мл из 500 мл | сумма: 12,50 ₽`
- Minimal startup-path verification on Linux:
  - `Получен сигнал остановки...`
  - `Клапан закрыт. Контроллер остановлен.`
  - `Конфигурация backend-сервера контроллера: SERVER_URL=http://cybeer-hub:8000 ...`
  - `Проверка backend при запуске успешна: url=http://cybeer-hub:8000/api/system/status status_code=200`
- Full `python3 main.py` in the temporary directory was blocked by a missing system dependency in that environment:
  - `ModuleNotFoundError: No module named 'smartcard'`
- This did not block startup-path validation of encoding because the hardware layer was stubbed for the verification run.

### General

- `python scripts/encoding_guard.py --all`
  - `OK: no UTF-8/mojibake/bidi-control issues found.`

## 6. Remaining risks

- The Linux host checkout at `/opt/beer-tap-system` was on an older dirty `master`, not on the current feature/hotfix branch. Backend verification was performed on the real host, but controller verification used an isolated temporary checkout to avoid mutating that dirty tree.
- If controller runtime is launched in environments with broken SSH/client-side character handling outside UTF-8, terminal rendering can still be affected after bytes leave Python. The controller itself now emits UTF-8 explicitly.
