# Feature Reference — Admin / Bartender App
**Beer Tap System — v1.0 (Phase 1 deliverables)**

**Purpose:** полный список фич для приложения бармена/администраторa, приоритеты, критерии приёма и прямое соответствие API (paths).  
Source of truth: `project_context.md` (beer-tap-system) + `project_context.md` (nfc-prototype).

---

## Summary: High-level priorities
- **High:** Quick Guest Lookup, Assign Card, Top-up Balance, Pour Status & Sync View, Emergency Stop, Keg/Tap Management, Multi-controller support (basic registration)
- **Medium:** Guest transaction history, Keg CRUD, Reports (pours), Inventory alerts
- **Low:** Mobile mode, advanced automation, remote valve control (deferred / needs hardware)

---

## Table of features (detailed)

| # | Category | Feature | Priority | Acceptance criteria (concrete) | API mapping (endpoint) |
|---:|---|---|---:|---|---|
| 1 | Guests | Quick Guest Lookup (name / phone / uid) | High | Search returns results <1s on local network; supports partial matches; returns guest id, name, balance, assigned cards. | `GET /api/guests?q=<term>` |
| 2 | Guests | Create / Edit Guest (UI form) | High | Create returns 201 with guest object; edit returns 200; validation for required fields. | `POST /api/guests/`, `PUT /api/guests/{guest_id}` |
| 3 | Guests | Assign / Unassign RFID card to guest | High | When Assign invoked: UI prompts "tap card", backend binds `uid` -> guest; success 200. Unassign sets card inactive. | `POST /api/cards/bind`, `POST /api/cards/unbind` |
| 4 | Guests | Top-up Balance (manual) | High | UI form sends amount+method; server records transaction and returns new balance; change reflected in guest listing. | `POST /api/guests/{guest_id}/topup` |
| 5 | Pours | Pour Status View (pending / confirmed / failed) | High | Dashboard shows pour list with status; pending highlighted; confirmations update within poll interval or websocket. | `GET /api/pours?status=pending` |
| 6 | Safety | Emergency Stop / Lockdown | High | Clicking Emergency sends command to backend; backend sets flag and controllers poll and stop pours immediately; audit log entry. | `POST /api/system/emergency` |
| 7 | Kegs/Taps | Keg CRUD | High | Create, Update, Delete keg; GET list returns inventory data; DB persist. | `POST /api/kegs`, `GET /api/kegs`, `PUT /api/kegs/{keg_id}`, `DELETE /api/kegs/{keg_id}` |
| 8 | Kegs/Taps | Assign Keg to Tap | High | UI selects keg and assigns to tap; tap state shows assigned keg. | `PUT /api/taps/{tap_id}/assign-keg` |
| 9 | Controllers | Controller Registration & Health | High | Controller can register with backend (controller_id, firmware, last_seen); backend shows controller list with heartbeat. | `POST /api/controllers/register`, `GET /api/controllers` |
|10 | Guests | Guest Transaction History | Medium | Guest page shows list of pours and top-ups; filter by date; CSV export. | `GET /api/guests/{guest_id}/transactions` |
|11 | Reports | Shift / Day pour report | Medium | Generate report for period; export CSV; includes totals and per-tap breakdown. | `GET /api/reports/pours?from=&to=` |
|12 | Ops | Open/Close Shift | Low | Shift open/close recorded; reports tied to shifts. | `POST /api/shifts/open`, `POST /api/shifts/close` |

---

## UI/UX patterns & small components (implementation notes)

- **Guest card component**: name, balance, assigned card(s) UIDs, quick actions: Top-up, Assign Card, View history.
- **Search bar**: global, debounce 250ms, returns guests/taps/kegs.
- **Pour list**: columns [time, guest, tap, volume, price, status(client_tx_id)], status color-coded.
- **Emergency control**: prominent red button in header; confirmation modal with reason input; logged in audit.

---

## Acceptance criteria (global)

- All **High** priority features must be implemented, tested and deployed to staging before enabling pilot.
- All endpoints must return standard HTTP codes and JSON body with `{ "success": true/false, "data": ..., "error": { code, message } }` pattern.
- All admin actions must create an audit log entry: `{ actor_user_id, action, target_id, timestamp, details }`.

---

## API mapping (per feature) — quick reference

> Note: This section is a concise map. Full OpenAPI fragment follows as separate file (`openapi_fragment.yaml`).

### Guests
- `GET /api/guests?q=<term>&limit=20&page=1` — search/list guests. Response: list of Guest.
- `POST /api/guests` — create guest. Body: `{ name, phone?, notes? }`.
- `GET /api/guests/{guest_id}` — guest detail.
- `PUT /api/guests/{guest_id}` — update guest.
- `POST /api/guests/{guest_id}/topup` — top-up balance. Body: `{ amount, method, note }`.
- `GET /api/guests/{guest_id}/transactions?from=&to=` — transaction history.

### Cards
- `POST /api/cards/bind` — bind card to guest. Body: `{ guest_id, uid }` (uid can be null to indicate "wait for tap" mode).
- `POST /api/cards/unbind` — unbind card. Body: `{ uid }` or `{ card_id }`.
- `GET /api/cards?guest_id=` — list cards by guest.

### Pours / Sync
- `POST /api/sync/pours` — existing sync endpoint for controllers (batch). Body: `{ pours: [ { client_tx_id, controller_id, tap_id, guest_card_uid, volume_ml, price, timestamp } ] }`
- `GET /api/pours?status=pending|confirmed|failed&limit=50` — view pours.

### System / Emergency
- `POST /api/system/emergency` — sets emergency flag. Body: `{ reason, actor_user_id }`
- `GET /api/system/status` — returns global flags (emergency, maintenance).

### Kegs & Taps
- `POST /api/kegs` — create keg. Body: `{ name, volume_ml, remaining_ml, cost_price, sell_price }`
- `GET /api/kegs` — list kegs.
- `PUT /api/kegs/{keg_id}` — update keg.
- `DELETE /api/kegs/{keg_id}` — remove keg.
- `PUT /api/taps/{tap_id}/assign-keg` — Body: `{ keg_id }`
- `GET /api/taps` — list taps (status, assigned_keg, last_pour)

### Controllers
- `POST /api/controllers/register` — Controller registers itself. Body: `{ controller_id, firmware_version, ip, capabilities }`
- `GET /api/controllers` — Admin list with last_seen, backlog_count.

---

## Implementation notes for devs

- Use `react-query` for data fetching / cache invalidation. Hook the search bar to cancel previous requests.
- For long-polling pour status updates, prefer WebSocket if available; otherwise poll `/api/pours?status=pending`.
- All critical actions (top-up, assign card, emergency stop) must be idempotent or generate unique action IDs to avoid duplication.
- Add audit log middleware in backend: wrap state-changing endpoints to create audit entries.

---

## QA scenarios (short list — for E2E)

1. **Guest create & assign card**: Create guest → open Assign modal → tap card (simulate) → backend binds → guest card visible.
2. **Top-up & pour flow**: Top-up guest balance → simulate pour on controller to consume amount → confirm pour synced and balance decreased.
3. **Emergency stop**: Trigger Emergency → controller receives flag on next poll and refuses pours → UI shows emergency status.
4. **Keg assign**: Create keg → assign to tap → tap shows assigned keg; pour records include keg_id.

---

## Next steps
- Use `openapi_fragment.yaml` as contract basis for frontend scaffolding.
- Create GitHub issues from `features-to-issues.csv`.
- Implement RBAC & authentication as prerequisite before pilot.

---
