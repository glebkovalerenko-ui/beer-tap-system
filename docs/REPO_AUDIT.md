# Аудит репозитория: код ↔ документация ↔ тесты ↔ архитектура

Дата: 2026-02-17

## 1) Карта репозитория

| Объект | Путь | Назначение | Состояние | Почему |
|---|---|---|---|---|
| Backend API | `backend/` | FastAPI + SQLAlchemy CRUD/API слой | ок (с замечаниями) | Структура модульная (`api/`, `crud/`, `models.py`, `schemas.py`), но есть несогласованность в тестовых зависимостях и env для тестов. |
| Backend entrypoint | `backend/main.py` | Инициализация FastAPI, роутеров, sync endpoint | ок | Единая точка входа, подключены роутеры `api/*`, есть `/api/token` и `/api/sync/pours`. |
| Безопасность backend | `backend/security.py` | JWT + internal token для контроллеров | подозрение | Секреты захардкожены (`SECRET_KEY`, `INTERNAL_API_KEY`) вместо env. |
| Контроллер RPi | `rpi-controller/` | Локальная обработка наливов, sync с backend | ок | Локальная SQLite + sync цикл + emergency stop polling. |
| Admin UI (web) | `admin-app/src` | Svelte SPA для админки | ок | Сборка проходит, есть stores/components/routes. |
| Admin desktop bridge | `admin-app/src-tauri` | Rust/Tauri bridge + NFC + API client | ок (с замечаниями) | `src/main.rs` содержит рабочие команды, но `src/lib.rs` выглядит как шаблонный остаток. |
| Контейнеризация | `docker-compose.yml`, `backend/Dockerfile` | Запуск PostgreSQL + backend | частично | В compose отсутствует сервис `admin-app`, хотя в документах он часто подразумевается. |
| CI | `.github/workflows/docs.yml` | Сборка и деплой документации | подозрение | Нет CI на тесты backend/frontend; проверяется только docs build. |
| Основная документация | `README.md`, `docs/*.md`, `docs/mvp/*` | Описание системы, API, MVP материалы | частично/устарело | Есть точные части, но есть и устаревшие/неподтвержденные утверждения и future-dated документы. |
| Схемы БД | `docs/sqlite_schema.sql`, `docs/postgres_schema.sql` | Референсные SQL-схемы | подозрение | Нужна регулярная сверка с SQLAlchemy/Alembic, автоматической проверки нет. |
| Миграции | `backend/alembic/` | Alembic scaffolding | подозрение | `models.Base.metadata.create_all()` в рантайме может расходиться с миграционной дисциплиной. |
| Тесты backend | `backend/tests/` | pytest + pytest-bdd + TestClient | частично | Тесты есть, но `requirements-test.txt` не содержит `pytest-bdd`; запуск без `DATABASE_URL` падает. |

## 2) Таблица соответствия документация ↔ код

| Утверждение из документации | Статус | Доказательство в коде/конфиге | Что исправить |
|---|---|---|---|
| Система запускается единым `docker-compose.yml` и отражает весь стек | ⚠️ частично | В `docker-compose.yml` описаны только `postgres` и `beer_backend_api`, сервиса admin-app/nginx нет. | В README и MVP-доках явно разделить: compose = backend+db; admin-app запускается отдельно (`npm run dev`/Tauri). |
| Используется dual-auth: JWT для админки + internal token для RPi | ✅ | `backend/security.py` (`oauth2_scheme`, `INTERNAL_API_KEY`, `get_current_user`) + `rpi-controller/sync_manager.py` (`X-Internal-Token`) | Добавить предупреждение о хранении секретов в env (сейчас захардкожены). |
| API endpoint `POST /api/token` принимает JSON | ❌ | Реализация использует `OAuth2PasswordRequestForm` (form-urlencoded) в `backend/main.py`. | Исправить docs/API_REFERENCE.md: формат `application/x-www-form-urlencoded`. |
| `GET /api/guests/{guest_id}` требует JWT | ❌ | В `backend/api/guests.py` этот endpoint без `Depends(get_current_user)`. | Уточнить в документации, что endpoint публичный (или закрыть endpoint кодом, если это ошибка требований). |
| FastAPI + Pydantic v2 | ✅ | Код использует FastAPI, схемы Pydantic, а предупреждение в тестах про deprecated `.dict()` указывает на v2-окружение. | Добавить задачу по миграции `.dict()` → `.model_dump()` в CRUD. |
| Архитектура admin-app: Svelte 5 + Tauri 2 | ✅ | `admin-app/package.json`, `admin-app/src-tauri/Cargo.toml`, rust-команды в `src-tauri/src/main.rs`. | Оставить, но синхронизировать контракт-файл с реальными командами и endpoint mapping. |
| CI проверяет качество кода и тесты | ❌ | Единственный workflow — `docs.yml` (сборка mkdocs). | Добавить workflows для backend pytest и frontend build/check. |
| Документация «источник правды» с датой 2026-02-17 | ⚠️ | `docs/INTERFACE_CONTRACT.md` и `project_context.md` имеют future-like датировки и формулировки без автоматической валидации. | Добавить статус документа (verified/needs-review) и процесс регулярной актуализации. |

## 3) Тесты и артефакты

### 3.1 Фактическая тестовая база
- Backend: `pytest`, `pytest-bdd`, `fastapi.testclient`, `httpx` (`backend/tests/*`, `backend/pytest.ini`).
- Frontend: формализованных тестов нет, но есть сборка через Vite (`admin-app/package.json`, script `build`).
- CI: автозапуск тестов отсутствует; есть только docs deployment workflow.

### 3.2 Найденные несоответствия по тестированию
1. `backend/requirements-test.txt` не включает `pytest-bdd`, хотя `backend/tests/conftest.py` его импортирует.
2. Тесты backend зависят от `DATABASE_URL` при импорте `database.py`; без env — падение до старта тестов.
3. При запуске с `DATABASE_URL=sqlite:///./test.db` часть тестов падает:
   - ожидание текста ошибки (`Not authenticated` vs `Could not validate credentials`),
   - интеграционные кейсы с `pours.price_per_ml_at_pour` (NOT NULL) в фикстурах.

### 3.3 Устаревшие/рискованные артефакты
- `project_context.md` — содержит неподтвержденные утверждения (например, про Nginx в активном деплое), требует пометки как аналитический/не-нормативный документ.
- `docs/mvp/phase/*`, `docs/mvp/changelog.md` — исторические отчеты, полезны как архив, но не как оперативный источник текущей архитектуры.

## 4) Реестр проблем

| ID | Тип | Серьёзность | Описание | Доказательства | Что сделать | Сложность |
|---|---|---|---|---|---|---|
| AUD-001 | дока/деплой | S1 | Документация описывает «полный стек через compose», но compose поднимает только backend+db | `docker-compose.yml`, `README.md` | Обновить инструкции запуска и разделить режимы запуска (API-only, full local). | Low |
| AUD-002 | тесты | S1 | Тесты не воспроизводимы из test requirements | `backend/requirements-test.txt`, `backend/tests/conftest.py` | Добавить `pytest-bdd` в test requirements; документировать `DATABASE_URL` для тестов. | Low |
| AUD-003 | безопасность/дока | S1 | Секреты захардкожены в backend | `backend/security.py` | Перенести `SECRET_KEY` и `INTERNAL_API_KEY` в env и обновить docs/env template. | Med |
| AUD-004 | дока/API | S2 | В docs ошибка формата запроса `/api/token` | `docs/API_REFERENCE.md`, `backend/main.py` | Исправить request format на form-urlencoded. | Low |
| AUD-005 | архитектура/дока | S2 | Нет CI на backend/frontend quality | `.github/workflows/docs.yml` | Добавить workflows: backend pytest, frontend build/check, rust `cargo check`. | Med |
| AUD-006 | дока/тесты | S2 | Документация по auth не совпадает с фактическим поведением некоторых endpoint | `docs/API_REFERENCE.md`, `backend/api/guests.py` | Уточнить public/secured endpoint list и зафиксировать security policy. | Med |
| AUD-007 | тесты/код | S2 | Часть BDD тестов падает на несогласованности схемы данных/ожиданий | `backend/tests/*`, ошибки pytest | Починить фикстуры и ожидания под текущую модель `pours` и auth errors. | Med |
| AUD-008 | дока | S3 | Нет общего индекса документации и статуса «актуально/архив» | `docs/` | Добавить `docs/INDEX.md` и пометки по жизненному циклу документов. | Low |

## 5) План работ

### Быстрые победы (1 день)
1. Обновить README и API_REFERENCE по фактическим командам запуска и auth-форматам.
2. Починить `backend/requirements-test.txt` (добавить `pytest-bdd`).
3. Добавить `docs/INDEX.md` и пометить архивные документы.

### 1 неделя
1. Добавить CI workflows: backend tests, frontend build/check, rust check.
2. Вынести секреты в env (`SECRET_KEY`, `INTERNAL_API_KEY`) + пример `.env.example`.
3. Стабилизировать backend-тесты (исправить фикстуры/ожидания).

### Долгосрочно
1. Автоматизировать сверку API-документации (генерация OpenAPI из running app и diff check).
2. Ввести политику docs-as-code: PR checklist + owner review для `docs/` и API changes.
3. Перевести исторические MVP документы в раздел `docs/archive/` с явными версиями.

## 6) Автоматизация (чтобы не повторялось)

Рекомендуемые проверки в CI:
1. `backend`: `pytest` + smoke запуск `uvicorn` + schema validation.
2. `admin-app`: `npm ci && npm run build` (и опционально `npm run check`).
3. `docs`: link check + markdown lint + проверка актуальности nav в `mkdocs.yml`.
4. PR-template чеклист:
   - [ ] обновил docs при изменении API/архитектуры
   - [ ] добавил/обновил миграции
   - [ ] проверил команды запуска локально
   - [ ] не добавил runtime-артефакты в git

