# Post-M6 / Pre-M7 Audit

Date: 2026-03-03
Repository: `beer-tap-system`
Remote: `origin = https://github.com/glebkovalerenko-ui/beer-tap-system.git`

## 1. Что было

### PR #39

- PR: [#39](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/39)
- Base / head: `master` <- `incident/free-pour-zero-balance`
- Mergeability at audit time: `MERGEABLE`
- Scope:
  - backend: `backend/crud/pour_crud.py`, `backend/crud/visit_crud.py`
  - tests: `backend/tests/test_incident_free_pour_zero_balance.py`, `rpi-controller/test_flow_manager.py`
  - docs/contracts/reports: `docs/API_REFERENCE.md`, `docs/INTERFACE_CONTRACT.md`, `docs/architecture/OPERATIONAL_MODEL_V1.md`, incident RCA artifacts
- Alembic migrations: none
- API contract impact:
  - `POST /api/visits/authorize-pour`: zero balance must fail before lock with `403 insufficient_funds`
  - `POST /api/sync/pours`: missing `pending_sync` for active lock must return `status="audit_only"` / `outcome="audit_missing_pending"`, emit audit action `sync_missing_pending`, and not create a pour row
- Risk: backend + controller contract + documentation
- Что меняет:
  - закрывает free-pour/zero-balance incident
  - усиливает authorize guard на insufficient funds
  - переводит missing-pending sync path в audit-only anomaly instead of accepted/free pour
- Что может сломать:
  - старые тесты/доки, которые ожидали terminal `rejected_missing_pending_authorize`
  - controller-side flow, если он полагался на старый response contract
- Как проверить:
  - `backend/tests/test_incident_free_pour_zero_balance.py`
  - `backend/tests/test_m6_insufficient_funds_clamp.py`
  - `rpi-controller/test_flow_manager.py`

### PR #40

- PR: [#40](https://github.com/glebkovalerenko-ui/beer-tap-system/pull/40)
- Base / head: `master` <- `infra/syncthing-dev-workflow`
- Mergeability at audit time: `MERGEABLE`
- Scope:
  - admin app / tauri runtime config
  - backend startup + docker health/startup checks
  - controller URL config / startup probe / logging
  - infra/dev workflow docs (`Syncthing`, backend URL runbooks)
- Alembic migrations: none
- API contract impact:
  - no new API routes
  - operational contract tightened around backend URL resolution and startup readiness
  - `GET /api/system/status` becomes explicit startup health target for controller/docker checks
- Risk: admin + controller + backend startup + infra
- Что меняет:
  - уводит dev workflow от Tilt к Syncthing
  - централизует backend base URL в admin-app/Tauri
  - делает backend fail-fast по `DATABASE_URL` и migration readiness
  - добавляет controller startup config logging + backend health probe
- Что может сломать:
  - desktop admin login/settings flow
  - backend startup, если `DATABASE_URL` или schema/head невалидны
  - controller boot, если `SERVER_URL`/DNS неверны
- Как проверить:
  - `npm run smoke:login-settings`
  - controller pytest
  - backend Postgres regression
  - smoke `GET /` and `GET /api/system/status`

### Предложенный и фактический порядок merge

1. `#39` первым: он фиксирует M4-M6 runtime contract по insufficient funds / missing pending sync и убирает риск free pour.
2. `#40` вторым: это широкий infra/admin/controller change-set, который безопаснее ребейзить на уже стабилизированный `master`.

Прямых file-level конфликтов между `#39` и `#40` не было. Порядок выбирался по контрактному риску, а не по конфликтам.

## 2. Что сделано

- Проверен исходный `master`: clean, linear, `alembic` single head.
- В `#39` найден и исправлен предмерж-блокер:
  - тест `backend/tests/test_m6_insufficient_funds_clamp.py` ожидал старый outcome `rejected_missing_pending_authorize`
  - docs частично содержали устаревшее описание того же path
- В `#39` добавлен commit:
  - `beb9c62` `tests: align missing-pending sync contract`
- PR `#39` merged into `master` via squash:
  - merge commit on `master`: `7a066b2`
- Для `#40` до rebase сохранён backup source head:
  - `origin/backup/infra-syncthing-dev-workflow-2026-03-03` -> `207186c`
- `#40` rebased onto fresh `master`, then pushed with `--force-with-lease`
- Для cleanup сохранён backup final rebased head:
  - `origin/backup/infra-syncthing-dev-workflow-final-2026-03-03` -> `0842c27`
- PR `#40` merged into `master` via squash:
  - merge commit on `master`: `79bde9e`
- После merge source branches удалены:
  - remote: `incident/free-pour-zero-balance`, `infra/syncthing-dev-workflow`
  - local: `incident/free-pour-zero-balance`, `infra/syncthing-dev-workflow`
- Старый хвост `origin/broken-state-backup` перенесён в backup namespace и удалён под старым именем:
  - `origin/backup/broken-state-backup-2026-03-03` -> `254a368`

## 3. Проверки

### Git / repo state

Commands:

```powershell
git status
git fetch --all --prune
git branch -vv
gh pr list --state open
```

Results:

- final local branch set: only `master`
- final `git status`: clean, `master...origin/master`
- open PRs after cleanup: none

### Alembic

Commands:

```powershell
cd backend
python -m alembic heads
docker compose exec -T beer_backend_api python -m alembic current
```

Results:

- `heads`: `0012_m6_rejected_sync (head)`
- `current`: `0012_m6_rejected_sync (head)`
- branching absent, single head preserved

### Backend tests (Postgres)

Command:

```powershell
docker compose exec -T beer_backend_api sh -lc "TEST_USE_POSTGRES=1 python -m pytest -q tests/test_m3_tap_lock.py tests/test_m4_offline_sync_reconcile.py tests/test_m5_shift_operational_mode.py tests/test_m5_shift_reports_v1.py tests/test_m5_time_source_invariants.py tests/test_m6_insufficient_funds_clamp.py tests/test_m6_lost_cards.py tests/test_incident_free_pour_zero_balance.py"
```

Result:

- `41 passed in 313.07s (0:05:13)` on the final `#40` branch before merge

### Controller tests

Command:

```powershell
python -m pytest -q rpi-controller/test_flow_manager.py rpi-controller/test_log_throttle.py rpi-controller/test_pour_session.py rpi-controller/test_terminal_progress.py
```

Result:

- `9 passed in 0.06s`

Notes:

- `rpi-controller/test_hw.py` was not used as a gate here because this environment lacks `gpiozero` / smartcard hardware dependencies and the file is hardware-bound despite the `test_*.py` name.

### Encoding guard

Command:

```powershell
python scripts/encoding_guard.py --all
```

Result:

- `OK: no UTF-8/mojibake/bidi-control issues found`

### Admin app smoke

Command:

```powershell
cd admin-app
npm run smoke:login-settings
```

Result:

- 6/6 smoke checks passed

Additional informational check:

```powershell
npm run check
```

Result:

- fails with `390` existing `svelte-check` errors across legacy JS typing / store typing / ambient typing gaps
- not introduced or fixed in this audit; treated as known deferred debt, not as a merge blocker for `#39/#40`

### Post-merge backend smoke

Host-to-container port `8000` is not reachable from this Windows session, so smoke was executed inside `beer_backend_api`.

Commands:

```powershell
docker compose exec -T beer_backend_api python - <<'PY'
import urllib.request
resp = urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)
print(resp.status)
print(resp.read().decode())
PY

docker compose exec -T beer_backend_api python - <<'PY'
import urllib.request
resp = urllib.request.urlopen('http://127.0.0.1:8000/api/system/status', timeout=5)
print(resp.status)
print(resp.read().decode())
PY
```

Results:

- `GET /` -> `200`, body `{"Status":"Beer Tap System Backend is running!"}`
- `GET /api/system/status` -> `200`, body `{"key":"emergency_stop_enabled","value":"false"}`

## 4. Alembic status

- single head: `0012_m6_rejected_sync`
- runtime DB current revision matches head
- no new migrations were introduced by `#39` or `#40`
- no alembic branching created during merge/rebase/cleanup

## 5. Backup refs and why they remain

All remaining non-merged remote tails are now intentionally under `origin/backup/*`.

| Backup ref | Commit | Why kept |
| --- | --- | --- |
| `origin/backup/broken-state-backup-2026-03-03` | `254a368` | migrated legacy nonstandard backup branch into backup namespace |
| `origin/backup/codex-conduct-full-repository-audit-rwij6k-2026-03-03` | `01706f1` | historical archival backup from prior cleanup |
| `origin/backup/codex-decompose-milestone-m1-t126xb-2026-03-03` | `1c76956` | historical archival backup from prior cleanup |
| `origin/backup/incident-free-pour-zero-balance-2026-03-03` | `beb9c62` | final source head of PR `#39` preserved before branch deletion after squash merge |
| `origin/backup/infra-syncthing-dev-workflow-2026-03-03` | `207186c` | pre-rebase source head of PR `#40` preserved before force-push |
| `origin/backup/infra-syncthing-dev-workflow-final-2026-03-03` | `0842c27` | final rebased source head of PR `#40` preserved before branch deletion after squash merge |
| `origin/backup/m5-time-db-source-2026-03-03` | `58f2478` | historical archival backup from prior cleanup |
| `origin/backup/m6-controller-terminal-ux-2026-03-03` | `5f07db0` | historical archival backup from prior cleanup |
| `origin/backup/m6-lost-cards-2026-03-03` | `b219588` | historical archival backup from prior cleanup |
| `origin/backup/pr-27-2026-03-03` | `a200979` | historical archival backup from prior cleanup |
| `origin/backup/pr-28-2026-03-03` | `36eb120` | historical archival backup from prior cleanup |
| `origin/backup/tilt-fix-config-sync-2026-03-03` | `033ff3c` | historical archival backup from prior cleanup |
| `origin/backup/tmp-36-onto-38-2026-03-03` | `05780bc` | historical archival backup from prior cleanup |

There are no non-backup remote branches left with unique commits outside `origin/master`.

## 6. Риски / известные долги, которые сознательно не трогались

- `admin-app` is not type-clean under `svelte-check`; current failure set is large and pre-existing, so it was documented but not refactored here.
- `rpi-controller/test_hw.py` remains hardware-environment dependent.
- Published Docker port `8000` is not reachable from this Windows session; smoke was executed from inside the container instead.
- No "rubles vs cents" migration or monetary-unit refactor was performed.
- No broad refactors beyond what was needed to make `#39/#40` mergeable and contract-consistent were performed.

## 7. Verdict

`Готово к M7` with documented non-blocking debt.

Why:

- both active PRs `#39` and `#40` are merged into `master`
- `master` is linear and clean
- alembic is `single head`
- mandatory backend/controller/encoding/smoke checks are green
- source branches for the merged PRs are removed
- remaining remote tails are intentionally archived under `origin/backup/*`
