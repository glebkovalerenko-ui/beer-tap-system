# Beer Tap System
# Operational Model v1
## (Integrated Self-Pour Core)

Version: 1.0  
Status: Approved for Implementation  
Scope: Single Location, Integrated with External POS (R-Keeper / iiko)

---

# 1. Product Positioning

## 1.1 Current Strategy

Beer Tap System is an **access-control and usage-metering platform** for self-pour bars.

The system:

- Manages guest identification
- Controls tap access
- Tracks pour volume
- Maintains operational balance
- Manages keg lifecycle and rotation
- Handles shift discipline
- Logs incidents and alerts

The system DOES NOT:

- Perform fiscalization
- Process payments
- Handle acquiring
- Act as a cash register

All financial operations are executed in external POS (R-Keeper / iiko).

---

## 1.2 Future Strategy

Architecture must allow:

- Adding internal financial module
- Operating independently from external POS
- Multi-location scaling
- Centralized monitoring

Core domain must remain independent from POS integration.

---

# 1.3 Operator UI Principles

Operator UI is a functional layer that must reflect backend invariants first.

- **Visit is the center**: operator actions are performed from an active visit context.
- **Visit opens by guest identity**: card may be absent at open time and can be issued/bound later.
- **Card bind/issue is separate**: issuing or binding card is handled as a separate operational step.
- **Lock state visible**: active tap lock (`active_tap_id`) is always explicit in UI.
- **Manual intervention visible**: force unlock / close actions are clear and require intent data where needed.
- **Audit transparency**: manual actions must remain traceable through backend audit trail and status transitions.

---

# 2. Domain Model

---

## 2.1 Location

Represents a physical bar location.

```

Location

* id
* name
* timezone

```

Note: Even if only one location exists now, the field must remain.

---

## 2.2 Guest

```

Guest

* id
* full_name
* phone
* passport_series
* passport_number
* birth_date
* consent_number
* created_at
* last_activity_at
* is_blocked

```

Rules:

- Passport is unique.
- Guests under 18 cannot receive a card.
- Passport modifications must be audit-logged.
- Balance is operational (not fiscal).

---

## 2.3 Visit

Represents a single bar visit session.

```

Visit

* id
* guest_id
* card_uid
* active_tap_id (nullable)
* status: active / closed
* opened_at
* closed_at
* closed_reason

```

Rules:

- One guest = one active visit.
- One visit = one active card.
- Card is deactivated when visit closes.
- Close visit card binding rule (atomic with visit close):
  - `card_returned=true` -> set card `status=inactive`, clear `card.guest_id` (card is reusable by another guest).
  - `card_returned=false` -> set card `status=inactive`, keep `card.guest_id` (card remains owned by the same guest).
- Active visits prevent shift closure.

---

## 2.4 LostCard

Tracks reported lost cards.

```

LostCard

* id
* card_uid
* guest_id
* visit_id
* reported_at
* reported_by

```

Behavior:

- If lost card UID is used в†’ block + critical alert.
- Visit entity is not overloaded with historical card records.

---

## 2.5 BeerType

```

BeerType

* id
* name
* style
* price_per_ml
* is_active

```

---

## 2.6 Keg

```

Keg

* id
* beer_type_id
* supplier
* declared_volume_l
* received_at
* connected_at
* disconnected_at
* remaining_volume_l
* status: warehouse / connected / empty / retired

```

---

## 2.7 Tap

```

Tap

* id
* controller_id
* current_keg_id
* status:
  active
  processing_sync
  out_of_keg
  maintenance
  error

```

---

## 2.8 PourSession

```

PourSession

* id
* visit_id
* tap_id
* keg_id
* started_at
* ended_at
* volume_ml
* cost
* sync_status: synced / pending_sync

```

Controller is the source of truth for volume.

---

## 2.9 Shift

```

Shift

* id
* location_id
* opened_at
* closed_at
* status

ShiftMember

* shift_id
* user_id
* joined_at
* left_at

```

Rules:

- Shift represents bar operating period.
- Staff rotation does NOT create new shift.
- Active visits must be closed before shift closure.

---

## 2.10 Alert

```

Alert

* id
* severity: info / warning / critical
* source_type
* source_id
* message
* created_at
* acknowledged_by
* resolved_at
* resolution_comment

```

---

# 3. Core Processes

---

# 3.1 Visit Opening

1. Guest registration or lookup.
2. Age verification.
3. External POS performs financial operation.
4. System opens Visit.
5. Card UID assigned.

---

# 3.2 Pour Authorization Flow

Before pour begins, backend verifies:

- Visit is active.
- Card UID matches visit.
- Card UID not in LostCard.
- active_tap_id is null.
- Balance в‰Ґ minimal_pour_cost.

If valid:

- active_tap_id = tap_id
- Controller receives balance
- Pour session starts

---

# 3.3 Simultaneous Card Usage Prevention

If active_tap_id is not null:

- Deny access
- Display: "Card already in use on Tap X"
- Log event

---

# 3.4 Connectivity Loss During Pour

If controller loses connection mid-session:

- Continue pour until completion.
- Deduct locally stored balance.
- Mark session as pending_sync.
- Tap в†’ processing_sync.
- No new card accepted.

---

# 3.5 Sync Recovery

When connection restored:

- Controller sends final volume.
- Backend updates balance.
- active_tap_id cleared.
- Tap returns to active.

If mismatch with manual entry в†’ create BalanceMismatch alert.

---

# 3.6 Server Unavailable

If backend is unavailable:

- All controllers block new pours.
- Active pours complete.
- Display: "Server unavailable".

Future: primary + secondary server replication.

---

# 4. Keg Lifecycle & Rotation

---

## 4.1 Keg Replacement

When keg is empty:

1. Tap в†’ out_of_keg.
2. System suggests next keg using FIFO:
   - Same BeerType
   - Status = warehouse
   - Oldest received_at.
3. Staff confirms replacement.
4. Keg в†’ connected.
5. Tap в†’ active.

---

## 4.2 Keg Alerts

- Info: <20% remaining
- Warning: <10% remaining
- Critical: 0% or no flow detected

---

# 5. Shift Closing Wizard

Before shift closure:

1. No active visits.
2. No pending_sync sessions.
3. Display unresolved alerts.
4. Equipment inspection confirmation.
5. Show shift summary.
6. Final confirmation.

Critical alerts do not block closure but must be acknowledged.

---

# 6. Shift Report

Minimum contents:

- Number of visits
- Total poured volume
- Total pour amount
- Cancelled pours
- Unresolved alerts
- Lost cards
- Staff involved in shift

---

# 7. POS Integration Boundary

System exposes integration interface:

```

POSAdapter

* notify_topup(guest, amount)
* notify_refund(guest, amount)
* notify_pour(guest, amount, beer_type)

```

MVP allows semi-manual synchronization.

---

# 8. Roles

Architecture supports roles.

MVP:
- Single unified role for all staff.

Future:
- Cashier
- Admin
- Manager

---

# 9. MVP Scope

Must include:

- Visit lifecycle
- Tap control
- Pour sessions
- Offline sync logic
- LostCard registry
- FIFO keg rotation
- Shift model
- Alert system
- Audit logging

---

# 10. Deferred Features

- Internal fiscal module
- Multi-location support
- Advanced card cryptography
- Keg weight sensors
- Complex warehouse accounting
- Inactivity fees
- Advanced role hierarchy

---

# End of Document
# 11. M4 Offline + Manual Reconcile State Machine (2026-02-25)

Operational source of truth:
- Controller detects and reports pour completion.
- Backend is the only component that changes operational lock state (`visit.active_tap_id`, `visit.lock_set_at`).

State transitions:
1. `authorize-pour` accepted -> `active_tap_id=tap_id`, `lock_set_at=now`, tap domain shown as `processing_sync`.
2. Normal sync accepted (`/api/sync/pours`) -> pour stored with `sync_status='synced'`, lock cleared.
3. Timeout/manual path (`/api/visits/{visit_id}/reconcile-pour`) -> pour stored with `sync_status='reconciled'`, lock cleared.
4. Late sync after manual reconcile:
   - same `short_id` -> `late_sync_matched` audit event, no second debit.
   - different/missing `short_id` -> `late_sync_mismatch` audit event, no second debit.

No-double-charge invariant:
- If visit is already unlocked and a late sync arrives, backend must not perform a second balance deduction.

Data keys introduced by M4:
- `pours.sync_status` (`pending_sync | synced | reconciled`)
- `pours.short_id` (6-8 chars)
- `visits.lock_set_at` (timestamp for UI-side timeout policy)

# 12. M5 Shift Operational Mode (2026-02-26)

Pilot scope implements a minimal but strict backend shift lifecycle.

Shift entity (implemented fields):
- `id`
- `opened_at` (not null)
- `closed_at` (nullable)
- `status` (`open | closed`)
- `opened_by` (nullable)
- `closed_by` (nullable)

Invariants:
- Only one `open` shift is allowed at a time.
- If no shift is open, operations are blocked:
  - `POST /api/visits/open` -> `403`
  - `POST /api/visits/authorize-pour` -> `403`
  - `POST /api/guests/{id}/topup` -> `403`

Shift close precheck:
- active visits exist -> `409` (`active_visits_exist`)
- pending sync pours exist -> `409` (`pending_sync_pours_exist`)

If precheck passes:
- shift is transitioned to `closed`,
- `closed_at` and `closed_by` are written by backend.

# 13. M5.X Shift Reports: X vs Z (2026-02-26)

X report:
- operational/intermediate report for current shift state;
- computed on demand;
- not required to be persisted in database.

Z report:
- final closing report for a shift;
- persisted in `shift_reports`;
- exactly one Z report per shift (idempotent create);
- available for historical lookup by date range.

v1 report focus:
- primary KPI is poured volume (`total_volume_ml`);
- money totals are stored in parallel (`total_amount_cents`) for future POS/cash evolution;
- keg section is currently placeholder (`not_available_yet`) until stable keg-to-pour linkage is expanded.

