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
**Complex payload structure for RPi controller synchronization**

This endpoint accepts batch pour data from RPi controllers and processes them atomically.

- **Authentication**: None (Public endpoint, but controllers should use internal token)
- **Response Model**: `SyncResponse`

**Request Body Structure:**
```json
{
  "pours": [
    {
      "client_tx_id": "rpi-001-2023-12-01-001",
      "card_uid": "04AB7815CD6B80",
      "tap_id": 1,
      "start_ts": "2023-12-01T10:30:00Z",
      "end_ts": "2023-12-01T10:30:15Z",
      "volume_ml": 500,
      "price_cents": 350
    },
    {
      "client_tx_id": "rpi-001-2023-12-01-002",
      "card_uid": "04AB7815CD6B81",
      "tap_id": 2,
      "start_ts": "2023-12-01T10:31:00Z",
      "end_ts": "2023-12-01T10:31:12Z",
      "volume_ml": 330,
      "price_cents": 231
    }
  ]
}
```

**Field Descriptions:**
- `client_tx_id`: Unique transaction identifier from RPi for idempotency
- `card_uid`: RFID card UID that performed the pour
- `tap_id`: Physical tap ID (integer)
- `start_ts`: Pour start timestamp (ISO 8601)
- `end_ts`: Pour end timestamp (ISO 8601)
- `volume_ml`: Volume poured in milliliters
- `price_cents`: Price in cents (integer)

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
  "poured_at": "datetime"
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

## Rate Limiting & Performance

- The `/api/system/status` endpoint is optimized for frequent polling by controllers
- Batch processing in `/api/sync/pours` handles multiple pours efficiently
- Pagination is available on list endpoints to manage large datasets
- Database connections use connection pooling for optimal performance

## M4 Endpoint Update (2026-02-25)

### POST `/api/sync/pours`
Additional required field in each pour item:
- `short_id` (string, 6-8 chars)

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
