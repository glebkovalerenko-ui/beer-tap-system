# Pilot Runbook

- Last reviewed against repository state: 2026-04-09
- Scope: reproducible bring-up for the current controlled pilot contour, including display path

## What this document is and is not

Это практический bring-up/runbook для текущего pilot contour в этом репозитории.

Это не:

- полный ops manual;
- production-grade deployment guide;
- one-click install;
- universal customer install guide для произвольной инфраструктуры.

Если источники расходятся, приоритет такой:

1. текущий код;
2. текущие конфиги и deploy-артефакты;
3. `PROJECT_STATUS.md`, `PILOT_SCOPE.md`, `SECURITY_BASELINE.md`, `README.md`;
4. свежие readiness/bring-up reports;
5. historical docs.

## 1. Target pilot contour

Этот runbook покрывает один контролируемый pilot contour:

- один Linux hub host с `postgres` и `beer_backend_api` через `docker compose`;
- одно operator workstation, рекомендуемый путь сейчас: Windows workstation с `admin-app` в web/dev режиме;
- один Raspberry Pi, на котором живут `rpi-controller`, `tap-display-agent` и локальный Chromium kiosk;
- один физический экран у крана;
- одна локальная сеть;
- один pilot tap contour, а не fleet и не multi-site.

Рекомендуемый topology split остаётся таким:

- Windows workstation: код/операторская работа с `admin-app`;
- Linux hub: backend + PostgreSQL;
- Pi: controller/display pair.

## 2. Required components and prerequisites

До старта нужны:

- Linux hub с Docker Compose и доступом к checkout в `/home/cybeer/beer-tap-system`;
- operator workstation с установленными `node` и `npm`;
- Raspberry Pi с checkout в `/home/cybeer/beer-tap-system`;
- физический tap hardware contour: NFC reader, GPIO relay/flow sensor, питание, сеть;
- физический монитор, который реально подключён к Pi; текущий pilot path подтверждён для portrait HDMI contour;
- доступ `sudo` на hub и на Pi;
- возможность править hub `.env` и Pi `/etc/beer-tap/device.env`;
- рабочая локальная связность `workstation -> hub` и `Pi -> hub`.

На hub рекомендуемый runtime path именно такой:

- repo checkout: `/home/cybeer/beer-tap-system`
- backend URL: `http://<hub-host>:8000`

На Pi рекомендуемый runtime path именно такой:

- shared env: `/etc/beer-tap/device.env`
- runtime file: `/run/beer-tap/display-runtime.json`
- runtime root: `/home/cybeer/.local/share/beer-tap`
- controller venv: `/home/cybeer/.local/share/beer-tap/venvs/controller`
- display-agent venv: `/home/cybeer/.local/share/beer-tap/venvs/display-agent`

OS packages, прямо подтверждённые deploy-артефактами для Pi:

- controller deps: `python3-venv python3-pip pcscd libccid python3-pyscard python3-gpiozero python3-lgpio`
- kiosk deps: `chromium lightdm labwc wlr-randr`

Дополнительные практические предпосылки:

- на Pi должен быть установлен рабочий `node`/`npm`, потому что `tap-display-client` собирается локально через `npm ci && npm run build`;
- если доставка кода на hub идёт через Syncthing, до bring-up нужно убедиться, что hub checkout действительно актуален; stale hub checkout уже был реальной причиной pilot drift;
- для воспроизводимого display/demo path нужен либо свежий controlled DB, либо заранее известный `tap_id`, который вы будете использовать на Pi.

## 3. Configuration files and secrets checklist

### Hub

Подготовьте `./.env` из `./.env.example`:

```bash
cd /home/cybeer/beer-tap-system
cp .env.example .env
```

В `./.env` обязательно заполните:

- `SECRET_KEY`
  Должен быть непустым и не placeholder.
- `INTERNAL_API_KEY`
  Основной internal token для controller routes.
- `INTERNAL_TOKEN`
  Для текущей pilot совместимости держите равным `INTERNAL_API_KEY`.
- `DISPLAY_API_KEY`
  Обязателен, если вы поднимаете display path. Для этого runbook он обязателен.
- `ENABLE_BOOTSTRAP_AUTH=true`
  Это текущий минимальный pilot login path.
- `BOOTSTRAP_AUTH_PASSWORD`
  Непустой pilot password для `admin`, `shift_lead`, `operator`.
- `CORS_ALLOWED_ORIGINS`
  Укажите реальные origin admin-app. Для рекомендованного web/dev path обычно:
  `http://localhost:5173,http://127.0.0.1:5173`

Оставьте консервативно:

- `ALLOW_INSECURE_DEV_SECRET_KEY=false`
- `ALLOW_LEGACY_DEMO_INTERNAL_TOKEN=false`

### Pi

Подготовьте `/etc/beer-tap/device.env` из `deploy/rpi/device.env.example`:

```bash
sudo install -d -m 0755 /etc/beer-tap
sudo cp /home/cybeer/beer-tap-system/deploy/rpi/device.env.example /etc/beer-tap/device.env
```

Обязательно заполните:

- `TAP_ID`
  Должен совпадать с tap в backend, который этот Pi обслуживает.
- `SERVER_URL`
  Должен быть реальным адресом hub, достижимым с Pi.
  Рекомендуемый current pilot path: `http://<hub-ip>:8000`, если `cybeer-hub` на Pi не резолвится.
- `INTERNAL_TOKEN`
  Должен совпадать с hub `INTERNAL_API_KEY`.
- `DISPLAY_API_KEY`
  Должен совпадать с hub `DISPLAY_API_KEY`.
- `DISPLAY_RUNTIME_PATH`
  По умолчанию оставляйте `/run/beer-tap/display-runtime.json`.
- `DISPLAY_AGENT_HOST`
  По умолчанию `127.0.0.1`.
- `DISPLAY_AGENT_PORT`
  По умолчанию `18181`.

### Workstation

Для рекомендуемого web/dev path не нужен отдельный env-файл, но перед стартом `admin-app` нужен backend URL:

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
```

Если hostname `cybeer-hub` не резолвится с workstation, используйте IP hub:

```powershell
$env:VITE_API_BASE_URL="http://192.168.0.110:8000"
```

### Token alignment checklist

Обязательные совпадения:

- hub `INTERNAL_API_KEY` = hub `INTERNAL_TOKEN` = Pi `INTERNAL_TOKEN`
- hub `DISPLAY_API_KEY` = Pi `DISPLAY_API_KEY`
- Pi `TAP_ID` = backend tap, который должен показываться и обслуживаться на этом устройстве

Не оставляйте:

- `replace-with-*`
- `change-me-*`
- `demo-secret-key`

## 4. Bring-up order

Рекомендуемый порядок именно такой:

1. Проверить, что hub checkout актуален и не находится в stale/Syncthing drift состоянии.
2. Подготовить hub `.env`.
3. Поднять `postgres` и `beer_backend_api`.
4. Проверить backend health, миграции и bootstrap login.
5. Поднять `admin-app` на workstation и проверить вход.
6. Убедиться, что в backend есть pilot tap для Pi `TAP_ID`.
7. Для internal demo/display shortcut при необходимости подготовить display content вручную или через seed path.
8. Подготовить на Pi `/etc/beer-tap/device.env`.
9. На Pi собрать `tap-display-client`.
10. На Pi провизионить внешние runtime venv.
11. На Pi установить и запустить `beer-tap-controller.service` и `tap-display-agent.service`.
12. Настроить graphical autologin + `labwc` autostart path и проверить kiosk.
13. Выполнить smoke checklist: backend, admin, controller, display, end-to-end.

## 5. Hub bring-up

### Recommended path

Для первого bring-up используйте прямой `docker compose`, а не systemd.

```bash
cd /home/cybeer/beer-tap-system
docker compose up -d --build postgres beer_backend_api
docker compose ps
```

Проверки после старта:

```bash
curl -fsS http://localhost:8000/
curl -fsS http://localhost:8000/api/system/status
docker compose exec -T beer_backend_api python -m alembic current
docker compose logs --tail=100 beer_backend_api
```

Что считать нормой:

- `GET /` отвечает;
- `GET /api/system/status` отвечает без 5xx;
- Alembic на момент этой ревизии дошёл до repository head, сейчас это `0016_guest_visit_card_consolidation`;
- backend стартует без fallback warning про insecure `SECRET_KEY`.

Проверка bootstrap login:

```bash
export PILOT_BOOTSTRAP_PASSWORD='replace-with-your-password'
curl -fsS \
  -X POST http://localhost:8000/api/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=admin" \
  --data-urlencode "password=$PILOT_BOOTSTRAP_PASSWORD"
```

Если login не взлетел, сначала проверьте:

- `ENABLE_BOOTSTRAP_AUTH=true`;
- `BOOTSTRAP_AUTH_PASSWORD` реально задан;
- `SECRET_KEY` не placeholder;
- backend поднят именно из актуального checkout.

### If the hub checkout is Syncthing-managed

Это не обязательная часть каждого bring-up, но для текущей split-модели это реальный риск и его нужно проверить до demo/pilot smoke.

Проверьте:

```bash
systemctl status beer-tap-sync-reconcile.timer --no-pager
journalctl -u beer-tap-sync-reconcile.service -n 30 --no-pager
```

Ожидаемое поведение:

- timer активен;
- reconcile не ругается на drift;
- hub не застрял на устаревшем working tree.

### Optional secondary path: boot-time systemd on hub

После успешного ручного bring-up можно включить boot-time units:

```bash
sudo install -m 0755 deploy/hub/beer-tap-sync-reconcile.sh /usr/local/bin/beer-tap-sync-reconcile.sh
sudo install -m 0644 deploy/hub/beer-tap-system.service /etc/systemd/system/beer-tap-system.service
sudo install -m 0644 deploy/hub/beer-tap-sync-reconcile.service /etc/systemd/system/beer-tap-sync-reconcile.service
sudo install -m 0644 deploy/hub/beer-tap-sync-reconcile.timer /etc/systemd/system/beer-tap-sync-reconcile.timer
sudo systemctl daemon-reload
sudo systemctl enable --now beer-tap-system.service beer-tap-sync-reconcile.timer
```

Это secondary path. Для первичного bring-up и диагностики проще и честнее стартовать вручную через `docker compose`.

## 6. Admin/operator workstation bring-up

### Recommended path

Рекомендуемый current path для runbook: web/dev Vite runtime на workstation.

```powershell
$env:VITE_API_BASE_URL="http://cybeer-hub:8000"
cd admin-app
npm ci
npm run dev
```

Откройте:

- `http://localhost:5173`

Вход:

- username: `admin`
- password: значение `BOOTSTRAP_AUTH_PASSWORD` из hub `.env`

Что проверить в operator surface:

- login проходит;
- приложение не упирается в CORS/URL mismatch;
- страницы `Today`, `Taps`, `Visits`/`Sessions`, `System` открываются;
- `System` не показывает тотальный backend/auth failure;
- открытие смены работает.

### Recommended data prep before touching the Pi

Для воспроизводимого pilot smoke на backend должен быть минимум один tap, который совпадает с Pi `TAP_ID`.

Рекомендуемый путь:

1. На чистом или controlled DB создать в Admin App pilot tap.
2. Для первого internal demo/display bring-up использовать `TAP_ID=1`.
3. После этого подготовить demo-friendly display content.

### Optional internal demo shortcut for display content

Если нужен быстрый internal demo path с уже подготовленным display catalog, а не ручное набивание beverages/kegs/display copy, используйте узкий seed-скрипт на hub.

Важно:

- это shortcut для internal demo/readiness, а не customer install story;
- он ожидает controlled data set;
- удобнее всего использовать его на fresh DB или когда intended pilot tap является первым tap в системе.

Сначала создайте tap в Admin App, затем:

```bash
cd /home/cybeer/beer-tap-system
docker compose exec -T beer_backend_api python dev_seed_tap_display_catalog.py --dry-run
docker compose exec -T beer_backend_api python dev_seed_tap_display_catalog.py
```

Если seed path вам не подходит, ручной минимум для display path такой:

- у pilot tap есть назначенный keg;
- tap находится не в `locked` и не в `empty`;
- для tap/display config включён display path;
- snapshot по этому tap не пустой.

### Secondary path

Tauri tooling в репозитории есть, но этот runbook не делает его primary flow. Для честного pilot bring-up используйте web/dev path выше.

## 7. Pi controller/display bring-up

### Step 1. Install OS/runtime prerequisites

Установите подтверждённые deploy-артефактами пакеты:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip pcscd libccid python3-pyscard python3-gpiozero python3-lgpio chromium lightdm labwc wlr-randr
```

Отдельно убедитесь, что на Pi уже доступны `node` и `npm`.

### Step 2. Build the display client on the Pi

```bash
cd /home/cybeer/beer-tap-system/tap-display-client
npm ci
npm run build
```

Это создаёт локальный `tap-display-client/dist`, который потом отдаёт `tap-display-agent` по `/display/`.

### Step 3. Fill `/etc/beer-tap/device.env`

Минимум для current pilot:

```dotenv
TAP_ID=1
SERVER_URL=http://192.168.0.110:8000
INTERNAL_TOKEN=replace-with-hub-internal-token
DISPLAY_API_KEY=replace-with-hub-display-token
DISPLAY_RUNTIME_PATH=/run/beer-tap/display-runtime.json
DISPLAY_AGENT_HOST=127.0.0.1
DISPLAY_AGENT_PORT=18181
```

Если `cybeer-hub` на Pi не резолвится, IP override на Pi сейчас является recommended pilot path.

### Step 4. Provision runtime venvs outside the repo

```bash
chmod 755 /home/cybeer/beer-tap-system/deploy/rpi/provision-runtime-venvs.sh
sudo /home/cybeer/beer-tap-system/deploy/rpi/provision-runtime-venvs.sh
```

Ожидаемый результат:

- controller venv создан в `/home/cybeer/.local/share/beer-tap/venvs/controller`
- display-agent venv создан в `/home/cybeer/.local/share/beer-tap/venvs/display-agent`

Это важно: runtime venv живут вне synced repo path.

### Step 5. Install and start controller/display services

```bash
cd /home/cybeer/beer-tap-system
sudo install -m 0644 deploy/rpi/beer-tap-controller.service /etc/systemd/system/beer-tap-controller.service
sudo install -m 0644 deploy/rpi/tap-display-agent.service /etc/systemd/system/tap-display-agent.service
sudo systemctl daemon-reload
sudo systemctl enable --now beer-tap-controller.service tap-display-agent.service
```

Проверки:

```bash
sudo systemctl status beer-tap-controller.service tap-display-agent.service --no-pager
sudo journalctl -u beer-tap-controller.service -u tap-display-agent.service --since "10 min ago" --no-pager
```

### Step 6. Verify local controller/display runtime

```bash
curl -fsS http://127.0.0.1:18181/health
curl -fsS http://127.0.0.1:18181/local/display/bootstrap
curl -fsS http://127.0.0.1:18181/local/display/runtime
sudo cat /run/beer-tap/display-runtime.json
```

Ожидаемое поведение:

- `/health` возвращает `status=ok`;
- `/local/display/bootstrap` возвращает snapshot для правильного `tap_id`;
- `/local/display/runtime` возвращает runtime payload и health block;
- runtime file существует и обновляется controller-ом.

### Step 7. Install the kiosk autostart hook

```bash
mkdir -p /home/cybeer/.config/labwc
install -m 0755 /home/cybeer/beer-tap-system/deploy/rpi/labwc-autostart /home/cybeer/.config/labwc/autostart
```

Текущий primary kiosk path:

- LightDM autologin
- `labwc` session
- `/home/cybeer/.config/labwc/autostart`
- `deploy/rpi/tap-display-kiosk.sh`
- Chromium kiosk на `http://127.0.0.1:18181/display/`

### Step 8. Configure graphical autologin

Это остаётся semi-manual шагом.

В репозитории есть kiosk launcher и `labwc` autostart hook, но нет one-shot provisioning для LightDM autologin/session selection. Для current pilot нужно вручную настроить:

- autologin пользователя `cybeer`;
- запуск именно `labwc` session.

После этого перезагрузите Pi или перезапустите graphical session.

### Step 9. Kiosk / portrait smoke

На устройстве проверьте:

- экран реально в portrait, а не landscape;
- Chromium открывает `http://127.0.0.1:18181/display/`;
- закрытие Chromium приводит к автоматическому relaunch;
- после `sudo systemctl restart tap-display-agent.service` экран восстанавливается без ручного редактирования файлов.

Полезный лог:

```bash
tail -n 100 ~/.local/state/tap-display-kiosk.log
```

Recommended assumptions этого path:

- output name: `HDMI-A-1`
- transform: `90`

Если монитор на реальном Pi определяется иначе, это уже manual pilot adjustment.

## 8. Smoke checklist

### Backend smoke

- `curl -fsS http://localhost:8000/` возвращает 200.
- `curl -fsS http://localhost:8000/api/system/status` возвращает 200.
- `POST /api/token` с `admin` и `BOOTSTRAP_AUTH_PASSWORD` возвращает `access_token`.
- `docker compose exec -T beer_backend_api python -m alembic current` показывает current head.

### Admin smoke

- `admin-app` открывается на `http://localhost:5173`.
- Login проходит без CORS/auth ошибок.
- `Today`, `Taps`, `System` загружаются.
- Открытие смены работает.
- Есть хотя бы один tap, который совпадает с Pi `TAP_ID`.

### Controller smoke

- `beer-tap-controller.service` активен.
- В journal нет постоянных 401/403 на `/api/visits/authorize-pour` и `/api/sync/pours`.
- `/run/beer-tap/display-runtime.json` существует и содержит правильный `tap_id`.
- Startup probe до backend проходит.

### Display smoke

- `GET http://127.0.0.1:18181/health` отвечает.
- `GET http://127.0.0.1:18181/local/display/bootstrap` отвечает и не пустой.
- `GET http://127.0.0.1:18181/local/display/runtime` отвечает.
- `http://127.0.0.1:18181/display/` открывается локально.
- Физический экран показывает не blank/gray desktop, а реальный tap display UI.
- После краткого backend outage локальные `/local/display/*` endpoints продолжают отвечать, а `backend_link_lost` переключается и потом восстанавливается.

### End-to-end pilot smoke

- Открыта смена.
- Создан или найден гость.
- Баланс пополнен.
- Открыт visit по карте.
- Карта приложена к Pi и display path показывает хотя бы один живой runtime state.
- Выполнен хотя бы один базовый operational loop: `idle -> authorized/denied -> pouring/finished` или `idle -> denied`.
- Хотя бы один pour дошёл до backend без застревания в бесконечном `pending_sync`.
- Visit можно корректно закрыть.

Если последние пункты не подтверждены на реальном устройстве, contour можно считать только partially brought up, но не demo-ready.

## 9. Failure points and quick diagnostics

- URL mismatch. Сначала сверяйте `VITE_API_BASE_URL` на workstation и `SERVER_URL` в `/etc/beer-tap/device.env`. Быстрый тест: `curl http://<hub>:8000/api/system/status` с workstation и с Pi.
- Token mismatch. Если controller/display routes дают 401, сравните hub `.env` и Pi `device.env`: `INTERNAL_API_KEY`/`INTERNAL_TOKEN` и `DISPLAY_API_KEY` должны совпадать.
- Stale hub checkout / Syncthing drift. Если backend выглядит “старым”, проверьте `journalctl -u beer-tap-sync-reconcile.service -n 30 --no-pager` и помните, что Windows остаётся single writer.
- Bootstrap login fails. Проверьте `ENABLE_BOOTSTRAP_AUTH=true`, `BOOTSTRAP_AUTH_PASSWORD`, `SECRET_KEY` и то, что backend реально поднялся из текущего checkout.
- Display agent healthy but kiosk blank. Сначала проверьте, что `tap-display-client/dist` собран, затем откройте локально `http://127.0.0.1:18181/display/` и посмотрите `~/.local/state/tap-display-kiosk.log`.
- Display agent healthy but no content. Частая причина: `TAP_ID` указывает на tap без assignment/display snapshot. Проверьте `/local/display/bootstrap` и pilot data prep.
- `controller_runtime_stale`. Проверьте `beer-tap-controller.service`, timestamp в `/run/beer-tap/display-runtime.json` и journal controller-а.
- Portrait не применился. Проверьте `wlr-randr`, реальное имя output и assumptions `HDMI-A-1` / `90`.
- Controller cannot authorize. Ищите в `journalctl -u beer-tap-controller.service` ошибки по `/api/visits/authorize-pour`, `shift_closed`, `lost_card`, `insufficient_funds`, `no_active_visit`.

## 10. What remains manual / pilot-grade

- Hub `.env` и Pi `/etc/beer-tap/device.env` заполняются вручную.
- Internal/display token alignment полностью manual.
- LightDM autologin и выбор `labwc` session не provision-ятся одним скриптом из репозитория.
- Наличие `node`/`npm` на Pi не обеспечивается deploy-артефактами.
- Display/demo data prep остаётся semi-manual. Seed-скрипт есть, но это internal shortcut, а не polished customer install flow.
- Финальная валидация display path требует живой проверки на физическом экране.
- Финальная валидация authorize/pouring/finished требует реальной карты и реального hardware contour.
- Kiosk supervision сейчас session-based, а не отдельный watchdog/fleet subsystem.
- Hub compose runtime всё ещё pilot/developer-style: bind-mounted backend code и `uvicorn --reload`.
- Если используется Syncthing delivery path, нужна дисциплина single-writer и контроль receive-only drift на hub.

## 11. Minimum readiness gate before demo/pilot discussion

Перед честной формулировкой “готово к demo/pilot discussion” все пункты ниже должны быть закрыты:

- hub backend и PostgreSQL поднимаются без ручных hotfix в коде;
- bootstrap login работает;
- operator workstation входит и открывает основные surfaces;
- выбранный pilot tap существует и совпадает с Pi `TAP_ID`;
- `beer-tap-controller.service` и `tap-display-agent.service` стабильно активны;
- physical kiosk реально показывает Tap Display UI в portrait;
- local display endpoints и runtime file живы;
- хотя бы один базовый live flow подтверждён на устройстве;
- команда знает, какие шаги в этом контуре остаются ручными и pilot-grade.

Если physical screen check или live device flow ещё не сделаны, это не go.

## 12. Recommended next docs

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [PILOT_SCOPE.md](PILOT_SCOPE.md)
- [SECURITY_BASELINE.md](SECURITY_BASELINE.md)
- [deploy/hub/README.md](deploy/hub/README.md)
- [deploy/rpi/README.md](deploy/rpi/README.md)
- [docs/reports/TAP_DISPLAY_REAL_PI_BRINGUP_AND_PORTRAIT_SMOKE.md](docs/reports/TAP_DISPLAY_REAL_PI_BRINGUP_AND_PORTRAIT_SMOKE.md)
- [docs/reports/TAP_DISPLAY_KIOSK_REBOOT_RECOVERY.md](docs/reports/TAP_DISPLAY_KIOSK_REBOOT_RECOVERY.md)
- [docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md](docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md)
