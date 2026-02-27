# Beer Tap System API Reference

## Overview

The Beer Tap System API is built with FastAPI and uses Pydantic v2 for data validation and serialization. This document provides comprehensive documentation of all available endpoints, authentication methods, and data models.

## Base URL

```
http://localhost:8000
```

## Authentication System

The API implements a dual-authentication system:

### 1. JWT Token Authentication (Admin/Web Interface)
- **Endpoint**: `POST /api/token`
- **Header**: `Authorization: Bearer <jwt_token>`
- **Usage**: For administrative operations and web interface access
- **Expiration**: 30 minutes
- **Payload**: 
  ```json
  {
    "username": "admin",
    "password": "fake_password"
  }
  ```

### 2. Internal Token Authentication (RPi Controllers)
- **Header**: `X-Internal-Token: demo-secret-key`
- **Usage**: For RPi controller communication
- **Purpose**: Allows controllers to register and sync data without JWT authentication

### Authentication Flow
1. **Admin Operations**: Use JWT token from `/api/token`
2. **Controller Operations**: Use internal token in `X-Internal-Token` header
3. **Public Endpoints**: Some endpoints (like system status) require no authentication

## API Endpoints

### System Endpoints

#### GET `/`
Health check endpoint to verify API is running.

**Response:**
```json
{
  "Status": "Beer Tap System Backend is running!"
}
```

#### POST `/api/token`
Authenticate and receive JWT token for admin operations.

**Request Format:** `application/x-www-form-urlencoded`

**Form fields:**
```text
username=<string>&password=<string>
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### Guests Management

#### POST `/api/guests`
Create a new guest account.
- **Authentication**: JWT required
- **Status**: 201 Created

**Request Body:**
```json
{
  "last_name": "Иванов",
  "first_name": "Иван",
  "patronymic": "Иванович",
  "phone_number": "+79211234567",
  "date_of_birth": "1990-01-15",
  "id_document": "4510 123456"
}
```

#### GET `/api/guests`
Get list of all guests with pagination.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0) - Number of records to skip
  - `limit`: int (default: 100) - Maximum number of records to return

#### GET `/api/guests/{guest_id}`
Get specific guest by UUID.
- **Authentication**: None

#### PUT `/api/guests/{guest_id}`
Update guest information.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "last_name": "Петров",
  "first_name": "Петр",
  "patronymic": "Петрович",
  "phone_number": "+79217654321",
  "date_of_birth": "1991-02-16",
  "id_document": "4511 654321",
  "is_active": false
}
```

#### POST `/api/guests/{guest_id}/cards`
Assign or register and assign a card to a guest.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "card_uid": "04AB7815CD6B80"
}
```

#### DELETE `/api/guests/{guest_id}/cards/{card_uid}`
Unassign card from guest.
- **Authentication**: JWT required

#### POST `/api/guests/{guest_id}/topup`
Top up guest balance.
- **Authentication**: JWT required
- **Operational Rule**: Requires an open shift (`POST /api/shifts/open`)

**Request Body:**
```json
{
  "amount": 500.00,
  "payment_method": "cash"
}
```

#### GET `/api/guests/{guest_id}/history`
Get guest transaction history.
- **Authentication**: JWT required
- **Query Parameters**:
  - `start_date`: date (optional) - Start date for history filter
  - `end_date`: date (optional) - End date for history filter

### Cards Management

#### POST `/api/cards/`
Register a new RFID card.
- **Authentication**: JWT required
- **Status**: 201 Created

**Request Body:**
```json
{
  "card_uid": "04AB7815CD6B80"
}
```

#### GET `/api/cards/`
Get list of all registered cards.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0)
  - `limit`: int (default: 100)

#### GET `/api/cards/{card_uid}/resolve`
Resolve full operational state for a card UID (single diagnostic endpoint for operator NFC lookup).
- **Authentication**: JWT required
- **Behavior**:
  - Works for any UID, regardless of lost status.
  - Returns lost-card flag/details, active visit (if any), guest/card context, and recommended next action.
  - Unknown UID is not an error; returns `is_lost=false` and nullable payload blocks.

**Response (example):**
```json
{
  "card_uid": "04A1B2C3D4",
  "is_lost": true,
  "lost_card": {
    "reported_at": "2026-02-26T11:15:00Z",
    "comment": "found near entrance",
    "visit_id": "550e8400-e29b-41d4-a716-446655440000",
    "reported_by": "admin"
  },
  "active_visit": {
    "visit_id": "550e8400-e29b-41d4-a716-446655440000",
    "guest_id": "6b5b0b90-0bd2-4f9c-a10f-dbe7d95d5f75",
    "guest_full_name": "Иванов Иван Иванович",
    "phone_number": "+79990001122",
    "status": "active",
    "card_uid": "04a1b2c3d4",
    "active_tap_id": 2,
    "opened_at": "2026-02-26T10:30:00Z"
  },
  "guest": {
    "guest_id": "6b5b0b90-0bd2-4f9c-a10f-dbe7d95d5f75",
    "full_name": "Иванов Иван Иванович",
    "phone_number": "+79990001122",
    "balance_cents": 12345
  },
  "card": {
    "uid": "04a1b2c3d4",
    "status": "active",
    "guest_id": "6b5b0b90-0bd2-4f9c-a10f-dbe7d95d5f75"
  },
  "recommended_action": "lost_restore"
}
```

#### PUT `/api/cards/{card_uid}/status`
Update card status.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "status": "lost"
}
```

### Taps Management

#### POST `/api/taps/`
Create a new tap.
- **Authentication**: JWT required
- **Status**: 201 Created

**Request Body:**
```json
{
  "display_name": "Кран в„–1"
}
```

#### GET `/api/taps/`
Get list of all taps.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0)
  - `limit`: int (default: 100)

#### GET `/api/taps/{tap_id}`
Get specific tap by ID.
- **Authentication**: JWT required

#### PUT `/api/taps/{tap_id}`
Update tap information.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "display_name": "Кран в„–1 (обновленный)",
  "status": "active"
}
```

#### DELETE `/api/taps/{tap_id}`
Delete a tap.
- **Authentication**: JWT required
- **Status**: 204 No Content
- **Business Rule**: Cannot delete tap with connected keg

#### PUT `/api/taps/{tap_id}/keg`
Assign keg to tap.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "keg_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### DELETE `/api/taps/{tap_id}/keg`
Remove keg from tap.
- **Authentication**: JWT required

### Kegs Management

#### POST `/api/kegs/`
Register a new keg.
- **Authentication**: JWT required
- **Status**: 201 Created

**Request Body:**
```json
{
  "beverage_id": "550e8400-e29b-41d4-a716-446655440000",
  "initial_volume_ml": 50000,
  "purchase_price": 10000.00
}
```

#### GET `/api/kegs/`
Get list of all kegs.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0)
  - `limit`: int (default: 100)

#### GET `/api/kegs/{keg_id}`
Get specific keg by UUID.
- **Authentication**: JWT required

#### PUT `/api/kegs/{keg_id}`
Update keg status.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "status": "empty"
}
```

#### DELETE `/api/kegs/{keg_id}`
Delete a keg.
- **Authentication**: JWT required
- **Status**: 204 No Content
- **Business Rule**: Cannot delete keg that is in use

### Beverages Management

#### POST `/api/beverages/`
Create a new beverage.
- **Authentication**: JWT required
- **Status**: 201 Created

**Request Body:**
```json
{
  "name": "Guinness",
  "brewery": "St. James's Gate Brewery",
  "style": "Stout",
  "abv": 4.2,
  "sell_price_per_liter": 700.00
}
```

#### GET `/api/beverages/`
Get list of all beverages.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0)
  - `limit`: int (default: 100)

#### GET `/api/beverages/{beverage_id}`
Get specific beverage by UUID.
- **Authentication**: JWT required

### Controllers Management

#### POST `/api/controllers/register`
Register or update controller (check-in).
- **Authentication**: None (Public endpoint)

**Request Body:**
```json
{
  "controller_id": "00:1A:2B:3C:4D:5E",
  "ip_address": "192.168.1.101",
  "firmware_version": "1.0.2"
}
```

#### GET `/api/controllers/`
Get list of all controllers.
- **Authentication**: JWT required

### System Management

#### GET `/api/system/status`
Get emergency stop status.
- **Authentication**: None (Public endpoint)

**Response:**
```json
{
  "key": "emergency_stop_enabled",
  "value": "false"
}
```

#### POST `/api/system/emergency_stop`
Set emergency stop status.
- **Authentication**: JWT required

**Request Body:**
```json
{
  "value": "true"
}
```

#### GET `/api/system/states/all`
Get all system state flags.
- **Authentication**: None
- **Note**: Hidden from public schema (debug only)

### Shifts

#### POST `/api/shifts/open`
Open a new operational shift.
- **Authentication**: JWT required
- **Behavior**: Only one open shift is allowed.
- **Errors**:
  - `409 Conflict`: Shift already open

#### POST `/api/shifts/close`
Close current open shift.
- **Authentication**: JWT required
- **Precheck blockers**:
  - `409 Conflict` with `detail=active_visits_exist`
  - `409 Conflict` with `detail=pending_sync_pours_exist`
- **Success**: Shift is marked `closed`, `closed_at` is set.

#### GET `/api/shifts/current`
Get current shift state.
- **Authentication**: JWT required
- **Response**:
  - `status=open` + shift payload when shift exists
  - `status=closed` + `shift=null` when no open shift

### Audit Logs

#### GET `/api/audit/`
Get audit log entries.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0)
  - `limit`: int (default: 100)

### Pours Management

#### GET `/api/pours/`
Get list of recent pours.
- **Authentication**: JWT required
- **Query Parameters**:
  - `skip`: int (default: 0)
  - `limit`: int (default: 20)

#### POST `/api/sync/pours` (CRITICAL ENDPOINT)
**Controller sync endpoint (duration-first contract)**

This endpoint accepts batch pour data from RPi controllers and processes them atomically.

- **Authentication**: None (Public endpoint, but controllers should use internal token)
- **Response Model**: `SyncResponse`

**Request Body Structure:**
```json
{
  "pours": [
    {
      "client_tx_id": "rpi-001-2023-12-01-001",
      "short_id": "A1B2C3",
      "card_uid": "04AB7815CD6B80",
      "tap_id": 1,
      "duration_ms": 15000,
      "volume_ml": 500,
      "price_cents": 350
    },
    {
      "client_tx_id": "rpi-001-2023-12-01-002",
      "short_id": "D4E5F6",
      "card_uid": "04AB7815CD6B81",
      "tap_id": 2,
      "duration_ms": 12000,
      "volume_ml": 330,
      "price_cents": 231
    }
  ]
}
```

**Field Descriptions:**
- `client_tx_id`: Unique transaction identifier from RPi for idempotency
- `short_id`: Short pour identifier (6-8 chars), required for sync/reconcile matching
- `card_uid`: RFID card UID that performed the pour
- `tap_id`: Physical tap ID (integer)
- `duration_ms`: Pour duration in milliseconds (primary contract field)
- `volume_ml`: Volume poured in milliliters
- `price_cents`: Price in cents (integer)

Backward compatibility:
- Legacy `start_ts` + `end_ts` are still accepted when `duration_ms` is missing.
- Backend may derive `duration_ms` from legacy fields, but DB event timestamps are always generated in Postgres.

**Response Structure:**
```json
{
  "results": [
    {
      "client_tx_id": "rpi-001-2023-12-01-001",
      "status": "accepted",
      "reason": null
    },
    {
      "client_tx_id": "rpi-001-2023-12-01-002",
      "status": "accepted",
      "reason": null
    }
  ]
}
```

**Status Values:**
- `accepted`: Pour successfully processed
- `rejected`: Pour failed validation
- `duplicate`: Pour with same client_tx_id already exists

## Data Models

### Beverage
```json
{
  "beverage_id": "uuid",
  "name": "string",
  "brewery": "string|null",
  "style": "string|null",
  "abv": "decimal|null",
  "sell_price_per_liter": "decimal"
}
```

### Keg
```json
{
  "keg_id": "uuid",
  "beverage_id": "uuid",
  "initial_volume_ml": "integer",
  "current_volume_ml": "integer",
  "purchase_price": "decimal",
  "status": "string",
  "tapped_at": "datetime|null",
  "finished_at": "datetime|null",
  "created_at": "datetime",
  "beverage": "Beverage"
}
```

### Tap
```json
{
  "tap_id": "integer",
  "display_name": "string",
  "status": "string",
  "keg_id": "uuid|null",
  "keg": "Keg|null"
}
```

### Guest
```json
{
  "guest_id": "uuid",
  "last_name": "string",
  "first_name": "string",
  "patronymic": "string|null",
  "phone_number": "string",
  "date_of_birth": "date",
  "id_document": "string",
  "balance": "decimal",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime",
  "cards": ["Card"],
  "transactions": ["Transaction"],
  "pours": ["Pour"]
}
```

### Card
```json
{
  "card_uid": "string",
  "guest_id": "uuid|null",
  "status": "string",
  "created_at": "datetime"
}
```

### Pour
```json
{
  "pour_id": "uuid",
  "volume_ml": "integer",
  "amount_charged": "decimal",
  "duration_ms": "integer|null",
  "sync_status": "pending_sync|synced|reconciled",
  "poured_at": "datetime",
  "authorized_at": "datetime|null",
  "synced_at": "datetime|null",
  "reconciled_at": "datetime|null",
  "started_at": "datetime|null",
  "ended_at": "datetime|null"
}
```

### PourResponse (Extended)
```json
{
  "pour_id": "uuid",
  "volume_ml": "integer",
  "amount_charged": "decimal",
  "poured_at": "datetime",
  "guest": {
    "guest_id": "uuid",
    "last_name": "string",
    "first_name": "string"
  },
  "beverage": "Beverage",
  "tap": "Tap"
}
```

### Controller
```json
{
  "controller_id": "string",
  "ip_address": "string",
  "firmware_version": "string|null",
  "created_at": "datetime",
  "last_seen": "datetime"
}
```

### AuditLog
```json
{
  "log_id": "uuid",
  "actor_id": "string|null",
  "action": "string",
  "target_entity": "string|null",
  "target_id": "string|null",
  "details": "string|null",
  "timestamp": "datetime"
}
```

## Database Field Mapping

The API models correspond exactly to the following database fields:

### Pour Table Critical Fields
- `price_per_ml_at_pour`: Decimal(10, 4) - Price per milliliter at time of pour
- `amount_charged`: Decimal(10, 2) - Total amount charged for the pour
- `client_tx_id`: String(100) - Unique transaction identifier from RPi
- `volume_ml`: Integer - Volume poured in milliliters

### Keg Table Fields
- `initial_volume_ml`: Integer - Starting volume when keg was full
- `current_volume_ml`: Integer - Current remaining volume
- `purchase_price`: Decimal(10, 2) - Total purchase cost of the keg

### Guest Table Fields
- `balance`: Decimal(10, 2) - Current account balance
- `is_active`: Boolean - Account status flag

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource successfully created
- `204 No Content`: Successful deletion
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required/failed
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate assignment)
- `500 Internal Server Error`: Server error

## Business Logic Rules

1. **Tap-Keg Assignment**: A tap can only have one keg, and a keg can only be assigned to one tap
2. **Keg Deletion**: Cannot delete a keg that is currently in use
3. **Card Assignment**: A card can only be assigned to one guest at a time
4. **Pour Processing**: All pours in a sync request are processed in a single database transaction
5. **Idempotency**: Duplicate pours with the same `client_tx_id` are rejected but marked as "duplicate"
6. **Emergency Stop**: When enabled, prevents all pouring operations system-wide
7. **Shift Gate**: `POST /api/visits/open`, `POST /api/visits/authorize-pour`, and `POST /api/guests/{id}/topup` return `403` when no shift is open

## Rate Limiting & Performance

- The `/api/system/status` endpoint is optimized for frequent polling by controllers
- Batch processing in `/api/sync/pours` handles multiple pours efficiently
- Pagination is available on list endpoints to manage large datasets
- Database connections use connection pooling for optimal performance

## M4 Endpoint Update (2026-02-25)

### POST `/api/sync/pours`
Additional required field in each pour item:
- `short_id` (string, 6-8 chars)
- `duration_ms` (integer, preferred)

DB-time contract:
- Backend does not trust controller absolute time for official event timestamps.
- `authorized_at` is set by DB at authorize (`pending_sync` creation).
- `synced_at` is set by DB when sync transitions to `synced`.
- `reconciled_at` is set by DB on manual reconcile.
- API responses do not include `server_time`.

Late-sync rule:
- when lock is already cleared, sync is accepted but must not create another charge;
- backend emits `late_sync_matched` or `late_sync_mismatch` audit event.

### POST `/api/visits/{visit_id}/reconcile-pour`
Manual timeout recovery endpoint.

Request body:
```json
{
  "tap_id": 1,
  "short_id": "A1B2C3",
  "volume_ml": 250,
  "amount": 125.00,
  "duration_ms": 5000,
  "reason": "sync_timeout",
  "comment": "operator entry"
}
```

Behavior:
- validates active visit lock on the same tap;
- creates manual reconciled pour (`sync_status = reconciled`);
- clears lock (`active_tap_id = null`, `lock_set_at = null`);
- idempotent by `(visit_id, short_id)`.

### POST `/api/visits/{visit_id}/close`
Card ownership behavior depends on `card_returned`:
- `card_returned=true`: card is set to `inactive` and unbound from the guest (`cards.guest_id = null`) in the same close transaction.
- `card_returned=false`: card is set to `inactive`, but guest binding is preserved (card remains owned by the same guest).
- `409 Conflict` with `detail=pending_sync_exists_for_visit` when unresolved `pending_sync` pours still exist for the visit.

## M5.X Report Endpoints Update (2026-02-26)

### GET `/api/shifts/{shift_id}/reports/x`
- Computes X report on the fly.
- Does not persist a record in `shift_reports`.

### POST `/api/shifts/{shift_id}/reports/z`
- Creates a persisted Z report for a closed shift.
- `409 Conflict` with `detail="Shift must be closed for Z report"` when shift is not closed.
- Idempotent: if Z exists for the shift, returns existing Z.

### GET `/api/shifts/{shift_id}/reports/z`
- Returns existing persisted Z report.
- `404 Not Found` when no Z report exists.

### GET `/api/shifts/reports/z?from=YYYY-MM-DD&to=YYYY-MM-DD`
- Returns compact list of Z reports by `generated_at` date range.
- `422` when `from > to`.

### Shift report payload v1

```json
{
  "meta": {
    "shift_id": "550e8400-e29b-41d4-a716-446655440000",
    "report_type": "X",
    "generated_at": "2026-02-26T12:00:00Z",
    "opened_at": "2026-02-26T09:00:00Z",
    "closed_at": null
  },
  "totals": {
    "pours_count": 12,
    "total_volume_ml": 3450,
    "total_amount_cents": 172500,
    "new_guests_count": 3,
    "pending_sync_count": 0,
    "reconciled_count": 1,
    "mismatch_count": 0
  },
  "by_tap": [
    {
      "tap_id": 1,
      "pours_count": 7,
      "volume_ml": 2100,
      "amount_cents": 105000,
      "pending_sync_count": 0
    }
  ],
  "visits": {
    "active_visits_count": 1,
    "closed_visits_count": 4
  },
  "kegs": {
    "status": "not_available_yet",
    "note": "Will be added when keg<->pour linkage is implemented"
  }
}
```

Notes:
- `total_volume_ml` is the primary KPI for current pilot mode.
- `total_amount_cents` is persisted for future POS/cash integration compatibility.
- `new_guests_count` counts guests created in shift window:
  - X report: `shift.opened_at .. now()`
  - Z report: `shift.opened_at .. shift.closed_at`
- `mismatch_count` is sourced from M4 audit events (`late_sync_mismatch`); if no such events exist in the range, value is `0`.

## M6 Lost Cards Update (2026-02-26)

### GET `/api/cards/{card_uid}/resolve`
Unified operator endpoint for NFC card lookup in Visits/Lost Cards UI.
- Authentication: JWT required
- Never returns `404` for unknown UID; uses nullable payload blocks + `recommended_action="unknown"`.
- `recommended_action` enum:
  - `lost_restore`
  - `open_active_visit`
  - `open_new_visit`
  - `bind_card`
  - `unknown`

### POST `/api/lost-cards`
Create lost card record (idempotent by `card_uid`).
- Authentication: JWT required
- If the card is already marked lost, existing record is returned.

Request body:
```json
{
  "card_uid": "04AB7815CD6B80",
  "reason": "guest_reported_loss",
  "comment": "reported at front desk"
}
```

### GET `/api/lost-cards`
List lost cards with optional filters.
- Authentication: JWT required
- Query params:
  - `uid` (optional, partial match)
  - `reported_from` (optional, ISO datetime)
  - `reported_to` (optional, ISO datetime)

### POST `/api/lost-cards/{card_uid}/restore`
Remove lost mark for card.
- Authentication: JWT required
- `404` when card is not in lost registry.

Response:
```json
{
  "card_uid": "04ab7815cd6b80",
  "restored": true
}
```

### POST `/api/visits/{visit_id}/report-lost-card`
Operator action from active visit card.
- Authentication: JWT required
- Preconditions:
  - visit exists and `status=active`
  - `visit.card_uid` is not null
- UID source is always `visit.card_uid` (no manual UID input and no lost-card tap required).
- Creates (or reuses) `lost_cards` record and returns visit + lost-card payload.

Response shape:
```json
{
  "visit": { "visit_id": "uuid", "card_uid": "04AB...", "status": "active" },
  "lost_card": { "card_uid": "04ab...", "reported_at": "2026-02-26T12:00:00Z" },
  "lost": true,
  "already_marked": false
}
```

### Authorization deny for lost card

`POST /api/visits/authorize-pour` performs hard check against `lost_cards`.
- If card is lost: `403 Forbidden`.
- Error body contains `detail.reason = "lost_card"`.
- Backend writes audit event `lost_card_blocked` with `{card_uid, tap_id, blocked_at}`.

## M5 Time Source Policy Update (2026-02-27)

### Global rule
- Official backend timestamps are DB-authored only (Postgres `now()`).
- API clients must not be treated as source of truth for `created_at/opened_at/closed_at/...` fields.

### Sync payload timing semantics (`POST /api/sync/pours`)
- `duration_ms` is the primary timing field for pour duration.
- Legacy `start_ts/end_ts` are accepted only as fallback to compute duration when `duration_ms` is absent.
- Backend writes official pour lifecycle timestamps using DB time (`func.now()` / DB defaults), not controller absolute timestamps.

### Shift report windows
- X report uses DB current time as right boundary.
- Z report uses `shift.closed_at` as strict right boundary.
