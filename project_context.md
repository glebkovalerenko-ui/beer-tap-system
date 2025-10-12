# Project Context: Beer Tap System (MVP)

*Last Updated: 2025-10-12*

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
Beer Tap System is an MVP hardware+software stack for a self-pour beer tap system designed to operate **local-first** (offline-capable). It features Raspberry Pi controllers that record pours locally (SQLite) and periodically synchronize to a central local server (FastAPI, PostgreSQL). A frontend admin UI (React / Vite) provides bartender/admin functionality. The entire system is packaged for reproducible deployment via Docker Compose.

**RU:**
Beer Tap System — это MVP аппаратно-программный комплекс для бара самообслуживания, построенный по принципу **локальной работы** (offline-capable). RPi-контроллеры с локальным журналом (SQLite) фиксируют наливы и периодически синхронизируют их с центральным локальным сервером (FastAPI + PostgreSQL). Админ-панель на React/Vite предоставляет интерфейс для бармена. Вся система развертывается через `docker-compose` для полной воспроизводимости.

---

### **2. Confirmed technical facts / Подтверждённые технические факты**

*   **Repository structure (confirmed):** `backend/`, `admin-ui/`, `rpi-controller/`, `nginx/`, `docs/`, `docker-compose.yml`, `README.md`.
*   **Primary server:** Python 3.11+ with FastAPI (`backend/`).
*   **Database:** PostgreSQL 15 (server) + SQLite with WAL mode (controller local DB).
*   **ORM / DB Layer:** SQLAlchemy (`backend/models.py`).
*   **Frontend:** React 18+ with Vite; `admin-ui/` contains React source and a multi-stage `Dockerfile`.
*   **Controller:** Python on Raspberry Pi (`rpi-controller/`), includes `main_controller.py`, `sync_client.py`. Local logging and pour emulation are implemented.
*   **Packaging / Deployment:** Docker Compose orchestrates all services. Nginx (`nginx/nginx.conf`) acts as a reverse proxy and serves the React static build.
*   **Offline-first design:** Controllers record transactions locally and sync to the server. The server endpoint (`/api/sync/pours/`) ensures idempotency via a unique `client_tx_id`.
*   **QA & SOP docs:** `docs/QA_Checklist.md` and `docs/SOP_Bartender.md` exist and define testing scenarios and operational procedures.

---

### **3. High-level architecture & data flow / Высокоуровневая архитектура и поток данных**

**Architectural Cornerstones:**
*   **Two Databases:** This is a deliberate choice for reliability. **PostgreSQL** is the central source of truth for all historical and relational data. **SQLite on the controller** is a robust, high-performance transactional journal, using WAL mode to ensure data integrity and minimize SD card wear even during power loss.
*   **Client-Generated IDs for Idempotency:** The controller generates a unique `client_tx_id` (UUID) for every pour *before* sending it to the server. This is the key to safe synchronization. If the network fails and the controller resends the same pour, the server sees the duplicate `client_tx_id` and simply discards it, preventing double-charging.
*   **Containerization:** The entire server-side application is defined in `docker-compose.yml`. This guarantees a consistent, reproducible environment, eliminating "it works on my machine" issues. The `healthcheck` for the `postgres` service prevents the backend from starting before the database is ready, solving potential race conditions.

**Key Data Flows:**
1.  **Guest Registration:** A bartender uses the **Admin UI** to send a new guest's data to the **FastAPI Backend**, which saves it in the **PostgreSQL** database.
2.  **Pour Emulation:** A guest taps a card on the **RPi Controller's** RFID reader. The controller's Python app generates a transaction with a unique `client_tx_id` and saves it to its local **SQLite** database with a `new` status.
3.  **Background Sync:** A background thread on the **RPi Controller** periodically sends a batch of `new` transactions to the `/api/sync/pours/` endpoint on the **FastAPI Backend**.
4.  **Server-Side Processing:** The **Backend** receives the batch. For each transaction, it checks if the `client_tx_id` already exists. If not, it saves the pour data to **PostgreSQL**, deducts the amount from the guest's balance, and confirms success.
5.  **Confirmation:** The **Backend** returns a list of statuses for each `client_tx_id` in the batch. The **Controller** receives this response and updates the status of the corresponding local transactions in **SQLite** to `confirmed`, removing them from the sync queue.

---

### **4. Implemented features (what is present in repo) / подтверждённый функционал**

#### Deployment & Infrastructure
*   [✅] **Dockerized Multi-Service Environment:** The entire system (`postgres`, `backend`, `admin-ui` with `nginx`) is orchestrated via `docker-compose.yml`.
*   [✅] **Reproducible Frontend Build:** Multi-stage `Dockerfile` for `admin-ui` creates a small, optimized production image served by Nginx.
*   [✅] **Database Initialization:** The PostgreSQL database is automatically initialized with the correct schema from `docs/postgres_schema.sql` on first run.

#### Backend API (`FastAPI`)
*   [✅] **Guest Management API:** Endpoints exist for creating (`POST /api/guests/`) and listing (`GET /api/guests/`) guests, with validation to prevent duplicates.
*   [✅] **Idempotent Sync Endpoint:** The crucial `/api/sync/pours/` endpoint accepts batches of pours, processes them, and prevents duplicate entries.
*   [✅] **CORS Configuration:** `CORSMiddleware` is enabled for development flexibility.

#### Frontend UI (`React`)
*   [✅] **Multi-Page Navigation:** A basic SPA structure with `react-router-dom` for navigating between Dashboard, Guests, and Taps pages.
*   [✅] **Guest List Display:** The "Guests" page successfully fetches and displays a list of registered guests from the backend API.

#### Controller Logic (`Raspberry Pi`)
*   [✅] **RFID Card Reading:** The controller can detect a card via `pyscard` and read its UID.
*   [✅] **Pour Emulation & Local Storage:** The controller simulates a pour, calculates the cost, and reliably saves the transaction to a local SQLite database.
*   [✅] **Robust Offline Buffering:** A background thread handles all network communication, ensuring that the main card-reading loop is never blocked by network latency or outages.
*   [✅] **Fault-Tolerant Sync:** The `sync_client.py` sends data in batches and correctly updates local statuses upon confirmation from the server.

---

### **5. How to run (Quick Start) — verified guidance / Как запустить (коротко)**

Before running: create `.env` in the repo root using the variables from the `README.md`.

1.  **Clone repository:**
    ```bash
    git clone https://github.com/glebkovalerenko-ui/beer-tap-system.git
    cd beer-tap-system
    ```
2.  **Build and start all services:**
    ```bash
    docker-compose up -d --build
    ```
3.  **Open `http://localhost/`** on the host that runs Docker.
4.  **Controller setup (on RPi):** Copy `rpi-controller/` to the device, run `setup.sh` to install dependencies, configure `config.py` with the server's IP address, and then run:
    ```bash
    source venv/bin/activate
    python3 main_controller.py
    ```

---

### **6. Known Limitations & Confirmed Gaps / Известные ограничения и подтверждённые пробелы**

*   **No Authentication/Authorization:** The admin UI and API are completely unprotected. There are no roles or user accounts.
*   **Physical Hardware is Emulated:** The controller does **not** interface with real flow meters or valves. The pour volume (`250ml`) is hardcoded.
*   **Incomplete Admin UI Functionality:**
    *   Guest creation/updating is only possible via API, not through the UI.
    *   Card assignment, balance top-ups, and Keg management are not implemented in the UI. The `TapsPage.jsx` is a placeholder.
*   **Single Controller Design:** The system is designed for a single controller (`TAP_ID = 1`). There is no backend logic to manage or differentiate between multiple controller devices.
*   **No Payment Gateway Integration:** The system only manages an internal balance. There is no code for interacting with payment service providers (PSP).

---

### **7. Security considerations (critical) / Вопросы безопасности (важно)**

*   **Credentials:** `.env` files must never be committed. A `.gitignore` entry is correctly in place for this. An `.env.example` file should be created.
*   **API Security:** The API endpoints lack authentication (JWT, OAuth2) and authorization (RBAC). This is a critical next step before any production use.
*   **Card Security:** The current implementation only reads card UIDs. If writing to cards (e.g., storing balance) is planned, secure protocols must be used to prevent card cloning or manipulation.

---

### **8. Recommended repo additions & housekeeping (immediate) / Рекомендации по улучшению репозитория**

1.  `project_context.md` (this file) — Add to repo root. ✅
2.  `.env.example` — Create to list required environment variables.
3.  `SECURITY.md` — Create to document security policies (key handling, access control).
4.  `tests/` — Add a directory for automated tests (e.g., `pytest` for backend, Vitest/Cypress for frontend).

---

### **9. Suggested prompts / Шаблоны промтов для ИИ (короткие)**

**For Backend Task:**
> *Using `project_context.md` as context, implement the API endpoints required for Keg Management. This includes creating `schemas.py` for Keg creation and updates, `crud.py` functions, and new routes in `main.py` for `POST /api/kegs`, `GET /api/kegs`, and `PUT /api/taps/{tap_id}/keg` to assign a keg to a tap.*

**For Frontend Task:**
> *Based on the existing `GuestsPage.jsx` and `api.js`, create a new component `GuestForm.jsx` that allows creating a new guest by sending a POST request to the `/api/guests/` endpoint. Include form state management, input validation for required fields, and error handling.*