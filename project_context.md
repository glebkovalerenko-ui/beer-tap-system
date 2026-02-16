# Project Context: Beer Tap System

*Last Updated: 2026-02-17*

**Repository:** `glebkovalerenko-ui/beer-tap-system` (public) — canonical source for this document.
**Prepared for:** Gleb Kovalerenko — based on analysis of `backend/main.py`, `admin-app/package.json`, `rpi-controller/flow_manager.py`, `docker-compose.yml`.

---

### **1. Technology Stack**

**Backend Server:**
- **FastAPI** - Modern Python web framework with automatic OpenAPI documentation
- **PostgreSQL 15** - Primary database server running in Docker container
- **SQLAlchemy** - ORM for database operations
- **JWT Authentication** - Token-based security with OAuth2PasswordRequestForm

**Frontend Admin Application:**
- **Svelte 5 + Tauri 2** - Modern reactive UI framework with Rust-based desktop application framework
- **Vite 6** - Fast build tool and development server
- **TypeScript 5.6** - Type-safe JavaScript development
- **Rust** - Low-level NFC access through Tauri backend

**RPi Controller:**
- **SQLite with WAL mode** - Local database for offline operation
- **Python 3** - Controller logic with modular architecture
- **gpiozero with LGPIOFactory** - GPIO pin management for hardware control
- **Hardware Integration** - Direct NFC and flow sensor control

**Infrastructure:**
- **Docker Compose** - Container orchestration for reproducible deployment
- **Nginx** - Reverse proxy and static file serving

---

### **2. Offline-First Architecture**

The system operates on a **thick client** model where Raspberry Pi controllers function as independent offline-capable units:

**RPi Controller (Thick Client):**
- Maintains local SQLite database with WAL mode for concurrent access
- Processes NFC card authentication and pour operations without network dependency
- Stores all pour data locally with unique transaction IDs
- Synchronizes with central server when connectivity is available

**Central Server (Source of Truth):**
- FastAPI backend serves as the authoritative data source
- PostgreSQL database maintains the complete system state
- Provides sync endpoints for batch data reconciliation
- Handles authentication and business logic validation

**Data Flow:**
1. RPi processes pours locally in real-time
2. Batch synchronization occurs via `/api/sync/pours` endpoint
3. Server validates and deduplicates using client transaction IDs
4. Conflict resolution prioritizes server as source of truth

---

### **3. RPi Controller Modular Architecture**

The Raspberry Pi controller implements a layered modular design:

**Hardware Abstraction Layer:**
- Direct interface with NFC readers (PC/SC protocol)
- Flow sensor integration (YF-S201 or compatible)
- Valve control mechanisms via gpiozero and LGPIOFactory
- Hardware state management and error handling

**Flow Manager (`flow_manager.py`):**
- Orchestrates the complete pour session lifecycle
- Manages card authentication and authorization
- Controls valve operations with safety timeouts
- Implements emergency stop functionality
- Calculates pricing and volume metrics
- Handles session cleanup and error recovery

**Database Layer:**
- Local SQLite with WAL mode for concurrent access
- Atomic transaction handling for data integrity
- Offline storage of pour records and system state
- Query optimization for sync operations

**Sync Manager:**
- Batch data transmission to central server
- Network connectivity monitoring
- Retry logic with exponential backoff
- Conflict detection and resolution
- Authentication token management

---

### **4. Localization Features**

**Russian Language UI:**
- The entire admin application interface is implemented in Russian
- All user-facing text, labels, and messages are localized
- System logs and error messages include Russian descriptions
- Documentation and API responses maintain Russian language support where applicable

**Implementation Details:**
- Svelte components contain hardcoded Russian text
- Backend error messages and logging in Russian
- NFC card authentication feedback in Russian
- Pour session status messages localized for Russian-speaking users

---

### **5. System Integration**

**API Architecture:**
- Modular router structure with separate endpoints for each domain
- RESTful design with proper HTTP status codes
- Comprehensive error handling and logging
- OpenAPI documentation automatically generated

**Security Model:**
- JWT-based authentication with bearer tokens
- Role-based access control framework
- CORS middleware for cross-origin requests
- Input validation and sanitization

**Deployment Model:**
- Docker Compose orchestrates all services
- PostgreSQL container with health checks
- FastAPI backend with hot reload for development
- Static file serving through Nginx reverse proxy

---

### **6. Key Technical Features**

**Real-time Processing:**
- Sub-second response times for NFC authentication
- Continuous flow monitoring during pour sessions
- Emergency stop capability with 3-second check intervals
- Timeout protection for valve operations

**Data Integrity:**
- Atomic database transactions
- Unique client transaction IDs for deduplication
- Comprehensive audit logging
- Rollback capabilities for failed operations

**Scalability:**
- Modular controller architecture supports multiple taps
- Horizontal scaling of backend services
- Efficient batch synchronization
- Resource-optimized SQLite operations

---

*This document reflects the current implementation state as of the source code analysis. All architectural decisions are based on the actual codebase structure and implementation patterns observed in the specified files.*