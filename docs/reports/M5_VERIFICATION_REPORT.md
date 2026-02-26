# M5 Verification Report (PR #31 / `m5-shift-operational-mode`)
Date: 2026-02-26
Reviewer workspace: `c:\Users\CatNip420\Documents\Projects\beer-tap-system`

## Environment (local)
- OS / shell: Windows (PowerShell 5.1.26100.7705)
- Python: 3.13.12
- Git: 2.51.0.windows.2
- Docker: 28.4.0
- Docker Compose: v2.39.4-desktop.1
- Node / npm: v22.20.0 / 10.9.3
- Cargo: 1.90.0

## Git State
### Initial state (before fixes)
Commands and key outputs:

```bash
git status
## m5-shift-operational-mode...origin/m5-shift-operational-mode

git branch --show-current
m5-shift-operational-mode

git rev-parse HEAD
555c86066be31d16d54d9ac44d33b0e0ceadcef3

git log --oneline -10
555c860 Implement M5 shift operational mode end-to-end
f71cd5d M4/stabilize runtime sync (#30)
214709f v0.4.0-m4-offline-safe (#29)
...
```

Branch sync check:

```bash
git fetch origin
# OK

git checkout m5-shift-operational-mode
Already on 'm5-shift-operational-mode'
Your branch is up to date with 'origin/m5-shift-operational-mode'.

git pull --ff-only
fatal: not something we can merge in .git/FETCH_HEAD: -current-state-of-admin-app-yz82aj' ...

git pull --ff-only origin m5-shift-operational-mode
Already up to date.
```

### Current state (after minimal fixes)

```bash
git branch --show-current
m5-shift-operational-mode

git rev-parse HEAD
711e00484a90c919cceeb1cb037a52338f16ad1f

git status
## m5-shift-operational-mode...origin/m5-shift-operational-mode [ahead 2]

git log --oneline -10
711e004 M5: remove unused debug import in tauri main
4695b73 M5: block visit close while pending sync exists
555c860 Implement M5 shift operational mode end-to-end
...
```

## Static Audit of PR #31
### New schema entities / migration `0006_m5_shift_operational_mode.py`
- New table: `shifts`
- Columns:
  - `id UUID PK`
  - `opened_at timestamptz not null default now()`
  - `closed_at timestamptz null`
  - `status varchar(20) not null default 'open'`
  - `opened_by varchar(100) null`
  - `closed_by varchar(100) null`
- Constraints / indexes:
  - check `status IN ('open','closed')`
  - index `ix_shifts_status(status)`
  - partial unique index `uq_shifts_one_open` where `status='open'` (one open shift invariant)

### Enforced invariants in backend
- `POST /api/visits/open` requires open shift (`403 Shift is closed`)
- `POST /api/visits/authorize-pour` requires open shift (`403 Shift is closed`)
- `POST /api/guests/{id}/topup` requires open shift (`403 Shift is closed`)
- `POST /api/shifts/close` blocked with `409 active_visits_exist` when active visits exist
- `POST /api/shifts/close` blocked with `409 pending_sync_pours_exist` when pending sync pours exist

### API changes
- Added shift endpoints:
  - `POST /api/shifts/open`
  - `POST /api/shifts/close`
  - `GET /api/shifts/current`
- Visit/guest gate behavior updated via `shift_crud.ensure_open_shift()` in:
  - `/api/visits/open`
  - `/api/visits/authorize-pour`
  - `/api/guests/{id}/topup`

### Admin-app changes (M5)
- `admin-app/src/stores/shiftStore.js`
  - backend-authoritative current/open/close shift state
  - close reason mapping: `active_visits_exist`, `pending_sync_pours_exist`
- `admin-app/src/components/shell/ShellTopBar.svelte`
  - open/close shift controls in top bar
- `admin-app/src/routes/Dashboard.svelte`
  - shift panel with open/close actions and state text
- `admin-app/src/App.svelte`
  - shift state fetch/reset on auth state changes
- `admin-app/src-tauri/src/api_client.rs` + `main.rs`
  - Tauri commands for `get_current_shift/open_shift/close_shift`

## DB & Migrations (PostgreSQL via docker compose)
Commands and key outputs:

```bash
docker compose down -v
# containers + volume removed

docker compose up -d postgres
# postgres started

docker compose run --rm beer_backend_api alembic upgrade head
Running upgrade ... -> 0006_m5_shift_operational_mode

docker compose up -d beer_backend_api
# backend started

curl.exe -fsS http://localhost:8000/
{"Status":"Beer Tap System Backend is running!"}

docker compose exec -T beer_backend_api alembic current
0006_m5_shift_operational_mode (head)
```

## Tests (Postgres mode)
### Requested commands: first raw attempt (as-is) and failure
Command:

```bash
TEST_USE_POSTGRES=1 python -m pytest -q tests/test_m5_shift_operational_mode.py
```

Full traceback/output:

```text
ImportError while loading conftest 'C:\Users\CatNip420\Documents\Projects\beer-tap-system\backend\tests\conftest.py'.
tests\conftest.py:58: in <module>
    _ensure_postgres_database_exists(TEST_DATABASE_URL)
tests\conftest.py:46: in _ensure_postgres_database_exists
    with engine_admin.connect() as conn:
...
E   sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "postgres" to address: Name or service not known
E
E   (Background on this error at: https://sqlalche.me/e/20/e3q8)
```

Reason:
- `.env` has `DATABASE_URL=...@postgres:5432/...` (Docker-internal hostname), not resolvable from host-run pytest.

### Re-run with explicit host-safe env (separate test DB)
Used env for all test commands:

```bash
TEST_USE_POSTGRES=1
DATABASE_URL=postgresql://beer_user:beer_password@localhost:5432/beer_tap_db
TEST_DATABASE_URL=postgresql://beer_user:beer_password@localhost:5432/beer_tap_db_test
```

Results:

```bash
python -m pytest -q tests/test_m5_shift_operational_mode.py
5 passed

python -m pytest -q tests/test_m4_offline_sync_reconcile.py
6 passed

python -m pytest -q tests/test_m3_tap_lock.py
5 passed

python -m pytest -q tests/test_visit_invariants.py
10 passed

python -m pytest -q
72 passed, 5 skipped, 91 warnings
```

Warnings in full suite:
- `gherkin_line.py` DeprecationWarning (`maxsplit` positional) x90
- `controller_crud.py` Pydantic v2 deprecation (`dict` -> `model_dump`)

## API Smoke (live backend)
### Scenario A: Shift gate
- `GET /api/shifts/current` -> `200` `{status:"closed"}`
- `POST /api/visits/open` with shift closed -> `403` `{detail:"Shift is closed"}`
- `POST /api/visits/authorize-pour` with shift closed -> `403` `{detail:"Shift is closed"}`
- `POST /api/shifts/open` -> `200` shift payload
- `POST /api/visits/open` with open shift -> `200` visit payload
- `POST /api/visits/authorize-pour` (prepared card/tap/topup) -> `200` `{allowed:true,...}`

### Scenario B: cannot close shift with active visit
- Open shift + active visit
- `POST /api/shifts/close` -> `409` `{detail:"active_visits_exist"}`
- Close visit
- `POST /api/shifts/close` -> `200` shift closed

### Scenario C on original PR state (before fix)
Observed blocker:
- authorize creates pending
- close visit succeeded
- `POST /api/shifts/close` -> `409 pending_sync_pours_exist`
- subsequent sync attempt -> `200` with result `rejected_inactive_guest_or_card`
- shift close remained blocked (`409 pending_sync_pours_exist`)

This was an operational deadlock (no API path to resolve pending after closing visit).

### Scenario C after applied fix (`4695b73`)
- `POST /api/visits/{id}/close` while `pending_sync` exists -> `409` `{detail:"pending_sync_exists_for_visit"}`
- `POST /api/sync/pours` -> `200` accepted (`pending_updated_to_synced`)
- `POST /api/visits/{id}/close` -> `200`
- `POST /api/shifts/close` -> `200`

## Admin-app checks
Commands:

```bash
cd admin-app
npm ci
npm run build
```

Results:
- `npm ci`: success; 2 vulnerabilities reported by npm audit (1 moderate, 1 high)
- `npm run build`: success (vite build completed)

Dev server:
- Not required for this verification run; functional UI paths were validated statically in files listed in static audit.

## Tauri / Rust
Command:

```bash
cd admin-app/src-tauri
cargo check
```

Results:
- Before fix: warning `unused import: debug` in `src/main.rs`
- After commit `711e004`: clean `cargo check` (no warnings from that import)

## Encoding / Bidi / Mojibake checks
Commands:

```bash
python scripts/encoding_guard.py --all
```

Output:
- `[encoding_guard] OK: no UTF-8/mojibake/bidi-control issues found.`

Additional grep checks requested:

```bash
git grep -n "\\u0432\\u0402"
# match only in scripts/encoding_guard.py pattern list

git grep -n "\\u0420\\u00A4"
# NO_MATCH

git grep -n "\\u0420\\u045F"
# NO_MATCH

git grep -n "\\u00D0"
# binary icon files only

git grep -n "\\u00D1"
# binary icon files only
```

Text-only confirmation:

```bash
git grep -nI "\\u00D0"
# NO_MATCH_TEXT

git grep -nI "\\u00D1"
# NO_MATCH_TEXT
```

Python scan for bidi/control chars (`U+202E`, etc.): `NO_MATCH`.

Conclusion:
- No hidden bidi/control artifacts found in tracked text files.
- No merge blocker from unicode/bidi in this run.

## Fixes Applied
1. `4695b73` — `M5: block visit close while pending sync exists`
- `backend/crud/visit_crud.py`
  - Added `409 pending_sync_exists_for_visit` guard in `close_visit`
- `backend/tests/test_m5_shift_operational_mode.py`
  - Updated tests for new safe behavior and preserved pending_sync shift blocker coverage
- `docs/API_REFERENCE.md`
  - Documented new `close visit` conflict condition

2. `711e004` — `M5: remove unused debug import in tauri main`
- `admin-app/src-tauri/src/main.rs`
  - Removed unused `debug` import

## Findings (severity)
### Blocker (resolved by fix)
- Original PR state allowed `close visit` with unresolved `pending_sync`, causing shift-close deadlock and failed sync recovery path.
- Status: resolved in `4695b73`.

### Major (open)
- Host-run pytest with raw command fails unless DB host is overridden from `postgres` to `localhost`.
- Impact: reproducibility/documentation issue for local reviewers running tests outside container network.

### Minor (resolved)
- Tauri unused import warning (`debug`) in `main.rs`.
- Status: resolved in `711e004`.

## Manual QA
### 1) Terminal errors are never empty
Use admin-app with backend running and check terminal logs (tauri + frontend console).

Steps:
1. Trigger `409`: call `POST /api/shifts/{id}/reports/z` while shift is still open.
2. Trigger `404`: request non-existing report, e.g. `GET /api/shifts/<random-uuid>/reports/x`.
3. Trigger `500`: simulate internal backend failure endpoint/path in local env.

Expected:
- Every error line contains non-empty text.
- Example non-empty outputs from smoke check:
  - `HTTP 404 /api/shifts/00000000-0000-0000-0000-000000000000/reports/x`
  - `{"reason":"active_visits_exist"}`
  - `HTTP 500 /api/sync/pours`

### 2) Validate `new_guests_count` in X and Z
Scenario:
1. Open shift.
2. Create 2 guests during open shift window.
3. Close shift.
4. Create 1 more guest after close.
5. Request X report (during open shift) and Z report (after close).

Expected:
- X report counts guests created from `opened_at` to current time.
- Z report counts guests created from `opened_at` to `closed_at`.
- In this scenario, `new_guests_count = 2` for Z.

## Container Postgres Verification (2026-02-26)
Commands run:

```bash
docker compose up -d postgres
docker compose run --rm beer_backend_api alembic upgrade head
docker compose run --rm beer_backend_api sh -lc "pip install -q pytest pytest-bdd httpx && TEST_USE_POSTGRES=1 python -m pytest -q tests/test_m5_shift_reports_v1.py"
docker compose run --rm beer_backend_api sh -lc "pip install -q pytest pytest-bdd httpx && TEST_USE_POSTGRES=1 python -m pytest -q"
python scripts/encoding_guard.py --all
```

Results:
- `tests/test_m5_shift_reports_v1.py`: `5 passed`
- Full suite in container: `77 passed, 5 skipped, 1 warning`
- `encoding_guard --all`: `OK` (no UTF-8/mojibake/bidi-control issues)

## Final Recommendation
**MERGE** (with fixes `4695b73` and `711e004` included).

If evaluating only original PR head `555c860` without these two commits, recommendation would be **DO NOT MERGE** due the Scenario C operational deadlock.
