# Documentation Index

## Актуальные документы

- `README.md` — быстрый обзор репозитория и запуск backend + PostgreSQL через Docker Compose.
- `docs/API_REFERENCE.md` — функциональное описание API (нуждается в регулярной сверке с `backend/api/*.py`).
- `docs/INTERFACE_CONTRACT.md` — контракт между Svelte/Tauri/FastAPI (частично устарел, см. `docs/REPO_AUDIT.md`).
- `docs/RPI_INTERNALS.md` — внутренняя логика контроллера Raspberry Pi.
- `docs/REPO_AUDIT.md` — технический аудит соответствия код ↔ документация ↔ тесты.

## Исторические / потенциально устаревшие документы

- `docs/mvp/*` — пакет MVP-материалов, сформированный под demo-фазу.
- `project_context.md` — аналитическая сводка, содержит неподтвержденные или устаревшие утверждения.
- `docs/baseline.md` — baseline-документ с предположениями, не всегда синхронизирован с текущей реализацией.
- `docs/QA_Checklist.md` — ручной чеклист, не привязан к CI.

## Рекомендуемый порядок чтения для новых участников

1. `README.md`
2. `docs/REPO_AUDIT.md`
3. `docs/API_REFERENCE.md`
4. `docs/INTERFACE_CONTRACT.md`
5. `docs/RPI_INTERNALS.md`
