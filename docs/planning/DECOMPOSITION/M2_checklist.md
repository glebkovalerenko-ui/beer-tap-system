# M2 Visit Model + Invariants — Execution Checklist

## Scope
- [ ] Add Visit as separate DB entity.
- [ ] Enforce one active visit per guest.
- [ ] Enforce one active visit per card.
- [ ] Deactivate card when visit closes.
- [ ] Keep top-up allowed without active visit (global guest balance).
- [ ] Do not add shift lifecycle logic (M5).
- [ ] Do not add offline sync logic (M4).

## Schema
- [ ] Add `visits` table.
- [ ] Add `pours.visit_id` nullable FK to `visits.visit_id`.
- [ ] Add partial unique indexes for active visit invariants.
- [ ] Keep `visits.active_tap_id` as `INT NULL` without FK (M3 placeholder).

## Backend
- [ ] Add Visit model + schemas + CRUD.
- [ ] Add open/close visit endpoints.
- [ ] Add active visit lookup by card endpoint.
- [ ] Wire visit checks into pour processing.
- [ ] Handle race conditions via IntegrityError -> 409 responses.

## Demo readiness
- [ ] Prepare reproducible verification scenarios.
- [ ] Validate via automated tests for key invariants.
