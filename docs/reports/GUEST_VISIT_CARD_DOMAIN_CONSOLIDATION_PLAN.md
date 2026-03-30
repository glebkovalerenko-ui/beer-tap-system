# Guest / Visit / Card Domain Consolidation Plan

## Status

- Historical intent in the project is mixed.
- The target model below is an explicit product-level consolidation decision.
- Sprint 1 implementation aligns runtime, APIs, lookup flows, migrations, and tests with this model.

## Scope And Purpose

This document defines the canonical operational model for:

- `Guest`
- `Visit`
- `Card`
- `Pour`
- lost-card handling
- tap/controller authorization
- operator lookup and close flows

The goal is to remove the dual operational truth between guest-owned cards and visit-owned cards, and to move the system to a pooled physical-card model centered on the active visit.

## Canonical Domain Rules

### Guests

- `Guest` stores identity, compliance, balance, and history.
- `Guest` does not own a persistent operational card.
- Guest-facing card history is derived from visit lifecycle and audit events, not from guest-owned card semantics.

### Cards

- `Card` is a physical RFID token from a reusable pool.
- `Card` is not recreated per visit.
- `new visit -> new card` means a new assignment from the pool, not a new `Card` entity.
- `Card.guest_id` is legacy compatibility only and must not be used as operational truth.

### Card Inventory Lifecycle

- `available`
- `assigned_to_visit`
- `returned_to_pool`
- `lost`
- `retired`

Rules:

- only `available` or `returned_to_pool` cards may be issued in normal flow;
- only one active visit may hold a card at a time;
- `lost` and `retired` cards are never authorizable for pours;
- `returned_to_pool` cards are explicitly reusable and treated as a high-risk migration/test area.

### Visits

- `Visit.card_uid` is the single canonical operational card relation.
- Normal operator flow requires a card at visit open time.
- Normal active cardless visit is not allowed.

Persisted operational visit states:

- `active_assigned`
- `active_blocked_lost_card`
- `closed_ok`
- `closed_missing_card`

### Normal Close

- Normal close requires scan-confirmed return.
- Canonical return path for sprint 1 is the operator-side NFC reader through Admin App / Tauri close flow.
- Manual confirmation without a scanned UID is not a valid normal close.
- Normal close succeeds only when:
  - the visit is `active_assigned`;
  - there is no blocking pending sync for the visit;
  - the scanned `returned_card_uid` matches the current normalized `visit.card_uid`;
  - the current card is still `assigned_to_visit`.
- Successful normal close sets:
  - visit `status = closed`
  - visit `operational_status = closed_ok`
  - card `status = returned_to_pool`
  - `returned_at`
  - `returned_by`
  - `return_method = operator_nfc`

### Lost Card

- Lost-card truth is visit-first.
- A lost-card mark immediately:
  - creates or confirms the `lost_cards` registry row;
  - sets card state to `lost`;
  - moves the visit to `active_blocked_lost_card`.
- A blocked lost-card visit:
  - remains open;
  - is not authorizable for pours;
  - cannot be normal-closed.
- Allowed resolution paths from `active_blocked_lost_card`:
  - `reissue_card_for_visit`
  - `service_close_missing_card`

### Reissue

- Reissue replaces the physical card assignment inside the same visit.
- Reissue is not implemented as guest-bind-first.
- After reissue:
  - the visit returns to `active_assigned`;
  - the new card becomes `assigned_to_visit`;
  - the old card stays `lost` until explicit inventory recovery.

### Service Close

- Service close is an explicit exception path.
- It closes the visit without confirmed card return.
- Service close sets:
  - visit `status = closed`
  - visit `operational_status = closed_missing_card`
  - current card remains `lost`

## Audit Trail Contract

The following visit-linked card lifecycle events are mandatory:

- `visit_card_issue`
- `visit_card_return`
- `visit_card_lost`
- `visit_card_reissue`
- `visit_service_close`

Each event must include machine-readable fields:

- `event_type`
- `occurred_at`
- `actor_id`
- `visit_id`
- `guest_id`
- `card_uid`
- `source_channel`
- `reason_code`
- `comment`
- `request_id`
- `previous_state`
- `next_state`

Additional expectations:

- `issue` records the assigned card and prior inventory state;
- `return` records the scanned UID, confirmation method, and match outcome;
- `lost` records the active visit context and blocked transition;
- `reissue` records old and new card UIDs and preserves visit continuity;
- `service_close` records the explicit exception path and its reason.

## Operator-Safe Lookup Outcomes

Card lookup is inventory-first and visit-first. It must not return guest-owned ownership as the primary operational answer.

### `active_visit`

- meaning: card is assigned to an active visit;
- recommended action: `open_visit_workspace`;
- allowed next actions:
  - `open_visit_workspace`
  - `mark_lost`
  - `normal_close_scan`

### `active_blocked_lost_card`

- meaning: card was marked lost on an active visit;
- recommended action: `open_visit_workspace`;
- allowed next actions:
  - `open_visit_workspace`
  - `reissue_card_for_visit`
  - `service_close_missing_card`

### `available_pool_card`

- meaning: physical pool card available for issuance;
- recommended action: `issue_on_open_visit`;
- allowed next actions:
  - `issue_on_open_visit`

### `returned_to_pool_card`

- meaning: returned card ready for reuse;
- recommended action: `issue_on_open_visit`;
- allowed next actions:
  - `issue_on_open_visit`

### `lost_card`

- meaning: card is lost and unavailable for normal operations;
- recommended action: `open_related_visit_if_any`;
- allowed next actions:
  - `open_related_visit_if_any`

### `retired_card`

- meaning: card is removed from active inventory;
- recommended action: `inventory_review`;
- allowed next actions:
  - `inventory_review`

### `unknown_card`

- meaning: UID is not registered in the pool;
- recommended action: `register_into_pool_if_inventory_flow_allows`;
- allowed next actions:
  - `register_into_pool_if_inventory_flow_allows`

## Guest History

Guest history is visit-derived.

Operator and guest surfaces must present card lifecycle through visit-linked events such as:

- visit opened with issued card;
- card returned on normal close;
- card marked lost during active visit;
- visit card reissued;
- visit service-closed with missing card.

Legacy guest-card bindings may remain in compatibility read-models temporarily, but they must not drive operator decisions.

## Controller And Sync Authorization

- Controller authorization resolves by normalized `Visit.card_uid`.
- Only an `active_assigned` visit may authorize a pour.
- Lost cards, retired cards, pool cards, and blocked visits are not authorizable.
- Offline sync processing uses the same visit-owned truth and normalized card resolution as authorize flow.

## Migration Stop Conditions

The rollout is not complete until all of the following are true:

- there are no case-only duplicate `card_uid` values;
- normal operator flow cannot create active cardless visits;
- operator APIs and operator UI no longer rely on guest-owned card semantics;
- lookup no longer returns guest-owned / no-active-visit semantics as normal operational truth;
- normal close no longer depends on `card_returned: bool` without scanned UID confirmation;
- returned cards safely transition to `returned_to_pool` and can be reused on later visits;
- lost cards cannot re-enter normal issuance or authorization accidentally;
- guest history is visit-derived and audit-derived.

## Delivery In Sprint 1

Implemented workstreams:

- visit-owned card relation enforced in backend services and schemas;
- pooled card inventory states introduced;
- scan-confirmed normal close flow implemented;
- blocked lost-card visit flow implemented;
- reissue and service-close endpoints implemented;
- operator lookup moved to inventory/visit-first outcomes;
- guest history augmented with visit-linked card lifecycle audit events;
- controller sync path aligned with normalized visit-owned card resolution;
- migration added with hard stop checks for case duplicates and cardless visits;
- backend tests updated to treat migration stop conditions as release gates.

Key implementation artifacts:

- migration: `backend/alembic/versions/0016_guest_visit_card_consolidation.py`
- domain services: `backend/crud/visit_crud.py`, `backend/crud/card_crud.py`, `backend/crud/pour_crud.py`
- API surface: `backend/api/visits.py`, `backend/api/lost_cards.py`
- operator/admin UI migration: `admin-app/src/routes/Guests.svelte`, `admin-app/src/routes/Visits.svelte`, `admin-app/src/routes/CardsGuests.svelte`

## Verification

Backend verification for sprint 1:

- full backend suite passes;
- migration guard logic is covered by focused domain tests;
- returned-to-pool reuse is explicitly covered as a high-risk scenario.
