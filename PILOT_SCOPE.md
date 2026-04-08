# Pilot Scope

- Last reviewed against repository state: 2026-04-08
- Evidence basis: current code, configs, deploy artifacts, selected current docs, selected current readiness reports

## What this document is and is not

Этот документ нужен для pre-sales, pilot discussions и первых внедрений. Он фиксирует честную рабочую границу между тем, что в текущем репозитории уже можно обсуждать как controlled first pilot, и тем, что пока рано обещать.

Это не коммерческое предложение, не договор, не обещание mass-rollout readiness и не полный эксплуатационный регламент.
Минимальный controlled-pilot auth/secrets contract зафиксирован в [SECURITY_BASELINE.md](SECURITY_BASELINE.md).

## 1. Pilot framing

Этот документ описывает наиболее реалистичный для текущего состояния репозитория пилот: single-location self-pour deployment в одной точке, с одним локальным hub/server контуром и ограниченным количеством tap/device контуров.

Цель такого пилота не в том, чтобы объявить продукт массово готовым. Цель в том, чтобы на реальной площадке проверить работоспособность связки backend, operator/admin surface, controller, tap display и основных recovery paths.

Самый безопасный стартовый масштаб для первого пилота:

- одна площадка;
- один hub host;
- одно операторское рабочее место;
- одна pilot controller/display pair на Raspberry Pi как минимальный device contour;
- при необходимости несколько кранов в той же точке только как осторожное повторение того же контура, а не как новый fleet/multi-site сценарий.

## 2. What is in scope for the pilot

В честный первый пилот можно включать только следующий подтверждённый scope:

- backend runtime на FastAPI + PostgreSQL как основной operational source of truth;
- текущую visit-centric доменную модель со сменами, гостями, картами, визитами, наливами, статусами кранов, журналами и отчётами;
- operator/admin surface из `admin-app/` как рабочее место для смены, кранов, визитов/истории, карт и гостей, lost-card flow, наливов, инцидентов, system view и tap screen settings;
- Raspberry Pi tap controller с локальной очередью, authorize-потоком, sync/reconcile путём и runtime-публикацией для экрана;
- tap display subsystem: backend snapshot/media API, display settings/media workflow, display-agent с локальным cache/runtime bridge и локальный kiosk UI на экране крана;
- базовые operational flows: open/close shift, guest lookup/create, top-up/refund, open visit with card, authorize pour, sync/reconcile, close visit, close shift;
- pilot-grade bring-up, smoke checks и сопровождение controlled deployment contour.

Для текущего пилота безопасно считать primary operator path именно card-at-open / visit-with-card. Исторические формулировки про cardless/card-later flow не должны использоваться как основная процедура площадки без отдельной инженерной проверки.

## 3. Recommended pilot topology

Наиболее реалистичная topology для первого пилота сейчас выглядит так:

- одна точка, одна локальная сеть, без SaaS или multi-site orchestration;
- один Linux host в роли hub machine;
- на hub host поднимаются `postgres` и `beer_backend_api` через `docker compose`, при желании через systemd units из `deploy/hub/`;
- один операторский клиент, для которого current repo reality лучше всего подтверждена как controlled workstation setup в split-модели "Windows workstation -> Linux hub";
- `admin-app` может использоваться как web runtime и как Tauri-based desktop shell, но честное пилотное обещание здесь должно звучать как "рабочее операторское место", а не как зрелый packaged desktop product для массовой выдачи;
- одна Raspberry Pi на pilot tap contour с controller + display-agent + local Chromium kiosk на этом же устройстве;
- каждая Pi работает в своём локальном runtime contour через `/etc/beer-tap/device.env`, external venvs и systemd units;
- Pi и workstation должны стабильно видеть backend по локальной сети; текущий репозиторий и readiness evidence допускают Pi-local IP override для hub, если hostname `cybeer-hub` на устройстве не резолвится.

Если площадка хочет сразу несколько кранов, наиболее честный подход сейчас - повторять тот же локальный contour внутри одной точки. Это не следует продавать как доказанную fleet-management модель.

## 4. Operational flows expected to be exercised in the pilot

Core flows, которые имеет смысл валидировать в первом пилоте:

- открытие смены и проверка operational gate;
- поиск или создание гостя;
- работа с картой и открытие визита по карте;
- пополнение баланса и, при необходимости, refund;
- authorize pour на контроллере, сам налив и последующий sync фактического pour в backend;
- наблюдение за состоянием крана, `pending_sync`, heartbeat и incident-like сигналами из операторских поверхностей;
- закрытие визита с возвратом карты или service-close path, если карта физически не возвращена;
- закрытие смены и базовые X/Z report flows.

Exception flows, которые полезно проверить хотя бы один раз в controlled pilot:

- manual reconcile / force-unlock, если `pending_sync` не закрывается штатно;
- lost-card report и recovery path через restore/reissue/service-close;
- tap display behavior при кратком backend loss или service restart;
- reboot/relaunch поведение display kiosk на pilot Pi.

Экзотические сценарии, новые интеграции и расширенные operational варианты не должны быть обязательной частью первого pilot core.

## 5. What is explicitly out of scope

В первый пилот не следует обещать:

- real POS или r_keeper integration;
- fiscal / EGAIS / Chestny Znak contour;
- cloud/SaaS topology, multi-site central control или fleet management;
- zero-touch provisioning, fully automated device imaging или OTA rollout;
- production-grade hardening, HA, DR, formal backup/restore regime или security audit posture;
- enterprise IAM, SSO и зрелый user lifecycle management;
- full observability stack, remote screenshot telemetry, dedicated kiosk watchdog или централизованное device supervision;
- broad certified hardware matrix;
- packaged desktop maturity claims для admin-app beyond controlled workstation setup.

## 6. Site prerequisites and assumptions

Со стороны площадки и пилотной установки нужны практические предпосылки:

- Linux hub machine с Docker/Compose, systemd и доступом к checkout path, который соответствует текущим deploy artifacts;
- стабильная локальная сеть между hub, операторским клиентом и Pi устройствами;
- возможность использовать предсказуемый hostname или согласованный IP-адрес hub для Pi-контуров;
- операторское рабочее место, на котором можно запустить `admin-app` и при необходимости вручную проверить backend URL/connectivity;
- для каждого pilot tap contour: Raspberry Pi device, совместимый с текущим controller/display path, плюс wiring и пакеты ОС, ожидаемые текущим controller stack;
- NFC reader и GPIO-based hardware contour, соответствующие текущему controller runtime, а не абстрактный "любой считыватель/любой контроллер";
- guest-facing monitor/display для tap screen; текущий pilot evidence подтверждён на portrait HDMI contour, а не на широком списке экранов;
- доступ к установке и поддержке `.env` на hub и `/etc/beer-tap/device.env` на Pi;
- настройка и согласование токенов и секретов, включая `SECRET_KEY`, internal token(s) и отдельный display read token;
- участие сотрудников площадки в bring-up, operator training, ручных smoke checks и recovery actions.

Важно: display token alignment остаётся частью semi-manual setup. Он нужен и на backend side, и на Pi side, и этот шаг не выглядит как полностью упакованная one-click конфигурация. Текущий top-level `.env.example` не описывает этот backend-side шаг как полноценно завершённый pilot contract.

## 7. Deployment reality for the pilot

Текущая deployment reality уже содержит usable pilot path, но она не production-grade.

Что уже реализовано и подтверждается репозиторием:

- `docker-compose.yml` поднимает backend + PostgreSQL и выносит media storage в отдельный volume;
- server-side runtime path уже существует, но его текущая форма всё ещё pilot/developer-style: bind-mounted backend code и `uvicorn ... --reload` внутри compose-сервиса;
- `deploy/hub/` содержит systemd units для compose stack и Syncthing-aware reconcile timer/service на Linux host;
- `deploy/rpi/` содержит конкретный pilot path для Pi controller/display pair: `device.env` contract, external runtime venvs, systemd units, local display-agent, kiosk launcher и portrait setup;
- display stack подтверждён и на уровне кода/тестов, и на уровне реального Pi bring-up/reboot recovery в ограниченном pilot contour;
- `admin-app` имеет реальный web runtime, build path и Tauri tooling с persisted backend URL model.

Что остаётся semi-manual и должно проговариваться заранее:

- на hub нужно вручную подготовить `.env`, compose/runtime path и при необходимости systemd units;
- если используется текущий engineering update workflow, он завязан на controlled repo delivery path, а не на customer-friendly updater;
- на Pi нужно собрать `tap-display-client`, подготовить `/etc/beer-tap/device.env`, прогнать provisioning script, установить units, настроить `labwc` autostart и выполнить локальные smoke checks;
- backend URL / token alignment между hub, workstation и Pi требует внимания и может быть источником drift;
- display installation и kiosk behavior всё ещё требуют on-device visual validation, а не только удалённых health endpoints.

Особенно важно для честного pilot framing:

- hub deploy path существует, но текущий compose/runtime ближе к pilot/developer deployment, чем к окончательно hardened server packaging;
- Pi/display deploy path существует и уже доказан на real-device contour, но остаётся pilot-grade и не превращается этим фактом во fleet-ready subsystem;
- admin-app стоит описывать как рабочую operator surface с web/runtime и Tauri shell, но не как массово отгруженный desktop product;
- Tauri tooling и runtime config в репозитории есть, но это не доказательство зрелого packaged rollout на много рабочих мест;
- security/config surface всё ещё требует инженерной дисциплины и явной ручной настройки.

## 8. Support and responsibility boundaries

Этот пилот предполагает вовлечённость с двух сторон.

Со стороны проекта обычно входит:

- подготовка и согласование pilot topology и конфигурации;
- помощь с initial bring-up hub, workstation и Pi contour;
- первичные smoke checks и верификация базового operational loop;
- сопровождение на раннем этапе пилота при инцидентах, рассинхронизации или конфигурационном drift;
- рекомендации по operator procedure и recovery actions, которые уже есть в текущем продукте.

Со стороны площадки обычно требуется:

- предоставить оборудование, сеть, питание и доступ для установки/обслуживания;
- выделить людей для pilot onboarding и для фактической ежедневной работы в смене;
- соблюдать согласованный рабочий путь площадки, особенно в части card-at-open, возврата карты и recovery flows;
- участвовать в ручных проверках после reboot, service restart, network issue или замены оборудования;
- обеспечивать безопасное хранение локальных токенов, URL-конфигов и env-файлов.

Что важно проговаривать заранее:

- пилот не подразумевает, что "всё разворачивается само";
- manual service restarts, log inspection, config corrections и operator recovery actions остаются частью текущей практической реальности;
- отдельные вмешательства инженера в early pilot не являются неожиданностью и не должны трактоваться как нарушение границы текущего scope.

## 9. Known pilot risks

Ключевые риски первого пилота в текущем состоянии:

- documentation mismatch risk: в репозитории ещё есть legacy wording и терминологическая инерция (`Visit` vs `Session`, старые формулировки про cardless flow);
- auth/security maturity risk: even after the controlled-pilot baseline, the project still relies on bootstrap local users, manual token coordination and non-enterprise auth boundaries, so this remains pilot-only rather than production-grade;
- semi-manual deployment risk: hub, workstation и Pi зависят от корректного совпадения URL, токенов, env и install steps;
- Syncthing/backend desync risk: текущий engineering update path чувствителен к single-writer discipline и может оставить hub на устаревшем working tree, если workflow нарушен;
- Pi/display recovery risk: kiosk path существенно улучшен, но остаётся session-based, а финальная visual truth на физическом экране всё ещё требует человеческой проверки;
- network and hardware dependence risk: стабильность LAN, резолв backend адреса, GPIO/NFC/wiring и конкретное поведение монитора/Wayland session имеют значение;
- operator adoption risk: текущий pilot contour требует дисциплинированного использования card-at-open и recovery paths; старые или неявные практики могут давать путаницу;
- unresolved productionization gaps: нет готовой истории для fleet automation, enterprise auth, полноценной observability и массового roll-out.

Эти риски не запрещают controlled first pilot, но их нужно проговаривать заранее, а не после запуска.

## 10. Pilot success criteria

Для первого пилота здесь разумны не абстрактные KPI, а прагматичные признаки успеха:

- backend + database contour, операторское рабочее место и хотя бы одна Pi controller/display pair стабильно работают в одной площадке и одной локальной сети;
- команда площадки может пройти базовый operational loop: открыть смену, найти или создать гостя, пополнить баланс, открыть визит по карте, выполнить налив, закрыть визит и закрыть смену;
- pour flow проходит без двойного списания и без потери фактического operational состояния при штатном sync;
- хотя бы один recovery path подтверждён вживую или в controlled repro: reconcile, force-unlock, lost-card recovery или display restart/degraded path;
- tap display работает как часть pilot contour, а не как отдельная демо-заглушка: показывает idle content и хотя бы один живой runtime state на реальном устройстве;
- операторы могут пользоваться текущими surfaces (`Today`, `Taps`, `Sessions`, `Cards & Guests`, `Pours`, `System`) для основных действий и базовой диагностики;
- по итогам пилота появляется конкретный список hardening/productization задач для следующего этапа, а не вывод "архитектурная основа неработоспособна".

## 11. Honest readiness summary

Good for pilot discussions:

- репозиторий уже достаточно конкретен, чтобы обсуждать не общую идею, а реальный первый pilot contour;
- границы backend/admin/controller/display contour и их non-goals можно формулировать без маркетинговых догадок.

Plausible for controlled first pilot:

- при одной площадке, одном hub host и одном аккуратно собранном Pi contour текущий репозиторий выглядит правдоподобной основой для controlled first pilot;
- это предполагает hands-on bring-up, конфигурационную дисциплину и раннюю инженерную вовлечённость.

Not yet suitable to present as mass-rollout-ready product:

- текущую auth/security модель нельзя честно продавать как production-grade;
- нет доказанной real POS/fiscal integration story;
- нет zero-touch/fleet deployment contour;
- нет оснований делать сильные заявления о масштабном packaged desktop rollout или enterprise observability.

## 12. Recommended next documents

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [docs/architecture/SYSTEM_ARCHITECTURE_V1.md](docs/architecture/SYSTEM_ARCHITECTURE_V1.md)
- [docs/architecture/OPERATIONAL_MODEL_V1.md](docs/architecture/OPERATIONAL_MODEL_V1.md)
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- [deploy/hub/README.md](deploy/hub/README.md)
- [deploy/rpi/README.md](deploy/rpi/README.md)
- [docs/reports/TAP_DISPLAY_REAL_PI_BRINGUP_AND_PORTRAIT_SMOKE.md](docs/reports/TAP_DISPLAY_REAL_PI_BRINGUP_AND_PORTRAIT_SMOKE.md)
- [docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md](docs/reports/SYNCTHING_BACKEND_DESYNC_RCA_AND_FIX_2026-03-25.md)
