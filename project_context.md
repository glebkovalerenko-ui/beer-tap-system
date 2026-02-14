# Project Context: Beer Tap System (Demo-Ready)

*Last Updated: 2026-02-14*

**Bilingual Edition (EN / RU)**

**Repository:** `glebkovalerenko-ui/beer-tap-system` (public) — canonical source for this document.
**Prepared for:** Gleb Kovalerenko — based on a full code review of the repository.

---

### ✦ **IMPORTANT — Scope and source of truth / ВАЖНО — границы и источник правды**

**EN (short):**
This `project_context.md` is constructed from a direct analysis of the repository's source code. It reflects the *actual implemented state* of the project. Treat this file as the canonical project summary when interacting with AI assistants and team members. Any functionality not described here should be considered unimplemented.

**RU (коротко):**
Этот файл составлен на основе прямого анализа исходного кода репозитория и отражает *фактическое состояние* проекта. Используйте его как единый и достоверный источник правды. Все предположения, которые были в предыдущих документах, были проверены и либо подтверждены, либо удалены.

---

### **1. Short overview / Краткое описание**

**EN:**
Beer Tap System is a Demo-Ready hardware+software stack for a self-pour beer tap system designed to operate **local-first** (offline-capable). It features Raspberry Pi controllers that record pours locally (SQLite) and periodically synchronize to a central local server (FastAPI, PostgreSQL). A frontend admin UI (Svelte / Vite) provides bartender/admin functionality. The entire system is packaged for reproducible deployment via Docker Compose.

**RU:**
Beer Tap System — это Demo-Ready аппаратно-программный комплекс для бара самообслуживания, построенный по принципу **локальной работы** (offline-capable). RPi-контроллеры с локальным журналом (SQLite) фиксируют наливы и периодически синхронизируют их с центральным локальным сервером (FastAPI + PostgreSQL). Админ-панель на Svelte/Vite предоставляет интерфейс для бармена. Вся система развёртывается через `docker-compose` для полной воспроизводимости.

---

### **2. Confirmed technical facts / Подтверждённые технические факты**

*   **Repository structure (confirmed):** `backend/`, `admin-app/`, `rpi-controller/`, `nginx/`, `docs/`, `docker-compose.yml`, `README.md`.
*   **Primary server:** Python 3.11+ with FastAPI (`backend/`).
*   **Database:** PostgreSQL 15 (server) + SQLite with WAL mode (controller local DB).
*   **ORM / DB Layer:** SQLAlchemy (`backend/models.py`).
*   **Frontend:** Svelte with Vite; `admin-app/` contains Svelte source and a multi-stage `Dockerfile`.
*   **Controller:** Python on Raspberry Pi (`rpi-controller/`), includes modular components:
    - `hardware.py`: Interfaces with YF-S201 flow sensor and ACR122U NFC reader.
    - `flow_manager.py`: Manages valve operations based on card presence.
    - `sync_manager.py`: Handles synchronization with the central server.
    - `database.py`: Local SQLite database with WAL mode.
*   **Packaging / Deployment:** Docker Compose orchestrates all services. Nginx (`nginx/nginx.conf`) acts as a reverse proxy and serves the Svelte static build.

---

### **3. API Security / Безопасность API**

**EN:**
- **Temporary Open Endpoints:**
  - `GET /api/guests/` and `POST /api/sync/pours/` are open for demo purposes (no JWT required).
- **Planned Security:**
  - All endpoints will require JWT authentication in production.
  - Role-based access control (RBAC) is partially implemented.

**RU:**
- **Временно открытые эндпоинты:**
  - `GET /api/guests/` и `POST /api/sync/pours/` открыты для демонстрации (без JWT).
- **Планируемая безопасность:**
  - Все эндпоинты будут требовать JWT-аутентификацию в продакшене.
  - Ролевое управление доступом (RBAC) частично реализовано.