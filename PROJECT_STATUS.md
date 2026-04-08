# Project Status

- Last reviewed against repository state: 2026-04-08
- Evidence basis: code, configs, deploy artifacts, selected current docs

## What this document is and is not

Этот документ фиксирует текущую реальность репозитория и помогает быстро выровняться по состоянию проекта. Это не маркетинговая страница, не полный продуктовый spec и не обещание production readiness.

Для честной рамки первого внедрения и pilot conversations читайте [PILOT_SCOPE.md](PILOT_SCOPE.md).
Для минимального auth/secrets baseline в controlled pilot читайте [SECURITY_BASELINE.md](SECURITY_BASELINE.md).

Если источники расходятся, приоритет такой: текущий код -> текущие конфиги и deploy-артефакты -> текущие entrypoint-документы -> недавние verification/readiness reports -> исторические документы.

## 1. What this project is

Beer Tap System в текущем репозитории - это система для self-pour сценария в одной точке: управление сменой, гостями и картами, визитами, наливами, операторскими поверхностями и tap display на устройстве у крана.

Это уже не просто концепт, но и не упакованный массовый продукт: в репозитории есть рабочие backend/admin/controller/display контуры и pilot-oriented deployment path, однако зрелость остаётся не production-grade.

## 2. Current product scope

- `backend/`: FastAPI + SQLAlchemy + Alembic, основное операционное состояние и API.
- `admin-app/`: операторская и административная поверхность на Svelte; в репозитории есть web build/runtime и Tauri tooling.
- `rpi-controller/`: логика Raspberry Pi контроллера крана, авторизация налива, локальная очередь и синк.
- `tap-display-agent/` + `tap-display-client/`: guest-facing display subsystem для экрана крана.
- Операционная модель вокруг `Shift`, `Visit`, `Card`, `Pour`, tap state и incident/operator narrative.
- POS присутствует только как integration seam/stub, а не как подтверждённая реальная интеграция.

## 3. Current architecture in practice

- Backend является операционным source of truth для смен, визитов, карт, наливов, статусов кранов, отчётов и display-конфигурации.
- Controller перед наливом обращается в backend за `authorize-pour`, хранит несинхронизированные данные локально и отправляет их через sync/reconcile APIs. Для экрана крана controller публикует runtime state в `/run/beer-tap/display-runtime.json`.
- Admin app работает как операторская оболочка поверх backend API и включает поверхности для смены, кранов, визитов/истории, карт и гостей, lost-card flow, наливов, system view и tap screen/display settings.
- Display path разделён: backend отдаёт snapshot/media для конкретного крана, display-agent забирает и кэширует их по read-only token, а display-client рендерит локальный guest UI и объединяет snapshot с runtime от controller.
- `Visit` остаётся центральным операционным агрегатом; `Pour` фиксирует lifecycle налива, `Shift` открывает/закрывает операционный режим, а `Card` связывает гостя с активным визитом.
- POS в текущем репозитории выражен через adapter seam (`notify_topup`, `notify_refund`, `notify_pour`) без доказанной live-интеграции с внешней системой.

## 4. Current terminology

- Canonical доменный термин в текущем коде и API - `Visit`.
- Текущая модель и API visit-centric: есть `Visit`-схемы, visit endpoints, visit lock semantics, open/close/reissue flows вокруг активного визита.
- Термин `Session` всё ещё встречается в operator/admin surfaces и части документов как UI/history/projection label: например, `SessionState`, `/sessions`, session history.
- По текущему коду нормальный operator-facing flow выглядит как card-at-open: request model открытия визита требует `card_uid`, а миграция консолидации данных ужесточает наличие карты у визита.
- При этом ambiguity полностью не исчезла: card-later wording и отдельные residual codepaths всё ещё встречаются в документации и части API surface. Поэтому этот документ не объявляет все card-later сценарии окончательно удалёнными; он только фиксирует, что primary current flow выглядит card-at-open.
- Если в legacy docs встречается `Session`, трактовать его нужно осторожно: чаще всего это историческое или UI-уровневое имя для visit history / operational state, а не отдельная canonical domain model.

## 5. What is working / implemented now

- Открытие и закрытие смены, включая X/Z reports и ограничения на закрытие при активных визитах или unresolved `pending_sync`.
- Visit-centric guest/card flows: создание и поиск гостей, top-up/refund, открытие активного визита, закрытие визита, lost-card и reissue-related handling.
- Pour flow: authorize -> `pending_sync` -> sync / reconcile / reject, включая tap lock и `processing_sync` состояние.
- Operator/admin projections и рабочие поверхности для `Today`, `Taps`, `Visits`, `Sessions`, `Cards & Guests`, `Lost Cards`, `Pours`, `System` и tap screens/display settings.
- Display subsystem в текущем репозитории: snapshot/media API на backend, display settings/media workflow в admin app, polling/cache/runtime bridge в display-agent, локальный guest UI в display-client.
- Deploy-артефакты для hub runtime и для Pi-пары controller/display: systemd units, runtime venv provisioning, device env contract, kiosk launch path.
- POS stub seam для будущих внешних sale hooks, но не полноценная интеграция.

## 6. Current deployment / runtime reality

- `docker-compose.yml` поднимает backend + PostgreSQL; это основной оформленный runtime path для серверной части.
- `admin-app/` можно запускать и собирать как Vite frontend; в репозитории также есть Tauri tooling, но этот документ не делает сильных заявлений о зрелости desktop packaging.
- `deploy/hub/` содержит Linux/systemd-артефакты для compose stack и Syncthing-aware reconcile flow на хосте `cybeer-hub`.
- `deploy/rpi/` содержит documented pilot path для одной Pi-пары controller/display: внешний runtime root, отдельные venv, systemd units, локальный agent, Chromium kiosk и portrait setup.
- Display installation reality остаётся semi-manual: есть build/install/enable/smoke steps и нужные артефакты, но нет доказательства полностью автоматизированного fleet rollout.
- В репозитории присутствует пилотный deployment path и runtime contract; этого недостаточно, чтобы честно называть текущий deploy production-grade.

## 7. Known limitations and non-marketing-ready areas

- Auth/security теперь доведён до controlled-pilot baseline, но не production-grade: explicit `SECRET_KEY`, explicit internal/display tokens, opt-in bootstrap auth и env-based CORS без enterprise IAM story.
- Документация всё ещё фрагментирована. Старые стадии, старые имена сущностей и промежуточные решения местами остаются в репозитории.
- Терминология `Visit` / `Session` очищена не полностью; для current truth важнее код и текущие API, чем старые словесные формулировки.
- Pi/display deployment pilot-grade: есть working path и deploy artifacts, но нет fleet management, remote watchdog или полноценной эксплуатационной телеметрии для множества устройств.
- POS integration не доведена до реальной внешней системы; в репозитории виден только stub seam.
- Репозиторий хорошо подходит для инженерного выравнивания и обсуждения пилота, но не даёт достаточных оснований заявлять mass-rollout readiness.

## 8. Truth hierarchy for documentation

Primary current truth:

- Этот `PROJECT_STATUS.md` как current-reality summary.
- [README.md](README.md) как основной репозиторный entrypoint.
- [docs/architecture/SYSTEM_ARCHITECTURE_V1.md](docs/architecture/SYSTEM_ARCHITECTURE_V1.md) как текущая архитектурная рамка, но с приоритетом кода при расхождениях.
- [docs/architecture/OPERATIONAL_MODEL_V1.md](docs/architecture/OPERATIONAL_MODEL_V1.md) как текущая операционная модель, снова с приоритетом кода и схем.
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) как практический API contract entrypoint.

Secondary supporting docs:

- [docs/operator/state-model.md](docs/operator/state-model.md) для словаря operator/backend состояний; полезен, но сохраняет `SessionState` label.
- [deploy/hub/README.md](deploy/hub/README.md) для server-side runtime path.
- [deploy/rpi/README.md](deploy/rpi/README.md) для Pi/display pilot deployment path.
- Недавние отчёты по actualization, localization, desync fix и tap display readiness как supporting evidence, а не как primary truth.

Historical context only:

- `docs/mvp/` и `docs/planning/`.
- Старые stage reports и phase-specific audits, если они описывают промежуточную реальность, а не текущее состояние default branch.
- Любые документы, где `Session`, старые visit/card assumptions или прежний deploy topology конфликтуют с текущим кодом, конфигами и deploy artifacts.

## 9. Recommended next docs to read

1. [README.md](README.md)
2. [docs/architecture/SYSTEM_ARCHITECTURE_V1.md](docs/architecture/SYSTEM_ARCHITECTURE_V1.md)
3. [docs/architecture/OPERATIONAL_MODEL_V1.md](docs/architecture/OPERATIONAL_MODEL_V1.md)
4. [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
5. [docs/operator/state-model.md](docs/operator/state-model.md)
6. [deploy/rpi/README.md](deploy/rpi/README.md)
7. [docs/reports/REPOSITORY_ACTUALIZATION_AUDIT_2026-04-02.md](docs/reports/REPOSITORY_ACTUALIZATION_AUDIT_2026-04-02.md)
8. [docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md](docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md)

## 10. Current readiness summary

Good for understanding and internal alignment:

- Репозиторий уже хорошо описывает основные компоненты, границы системы и текущий working scope.
- На его основе можно выровнять внутреннюю команду по visit-centric модели, backend/controller/display архитектуре и реальным ограничениям.
- `PROJECT_STATUS.md` можно использовать как первую точку чтения перед дальнейшей документационной чисткой.

Good for demo / pilot discussions:

- В репозитории реализованы backend/admin/controller/display контуры, которые достаточно конкретны для demo и pilot planning.
- Есть deploy artifacts и documented pilot path для hub runtime и для одной Pi controller/display пары.
- Есть основания обсуждать pilot readiness по отдельным контурам, но не делать сильных заявлений сверх того, что подтверждено в коде и deploy artifacts.

Not yet mass-rollout-ready:

- Нет достаточных оснований считать auth/user management production-grade.
- Нет подтверждённой полноценной POS integration story.
- Нет доказанной fully automated device/fleet deployment model для Pi/display части.
- Документация и терминология ещё требуют дальнейшей консолидации, хотя базовая current-reality точка правды теперь может быть зафиксирована.
