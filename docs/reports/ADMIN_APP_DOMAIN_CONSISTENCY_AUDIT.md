# Admin App Domain Consistency Audit

Date: 2026-03-30  
Branch: `investigation/admin-app-domain-consistency-audit`

This report is an audit only. No broad behavioral fix was applied in this task.

Audit method:

- code-level tracing across `admin-app`, `backend`, `rpi-controller`, `tap-display-agent`, and `tap-display-client`;
- targeted API reproduction with an isolated in-memory FastAPI/TestClient harness following the same override pattern used by backend tests;
- controller authorization/runtime traced through `rpi-controller` code paths.

Important note about evidence:

- direct local runtime reproduction against the workspace default PostgreSQL target was not possible because the configured `postgres` host is not reachable in this environment;
- the core business paths were still reproduced deterministically through the backend app itself;
- background async audit logging attempted the default DB and logged connection errors during those reproductions, but the main request/response behavior under audit was unaffected.

## 1. Problem statement

Observed symptom chain:

1. In the guest card, a card is already bound and visible.
2. In the active visit for the same guest, the UI still shows `Без карты`.
3. When the card is used on the tap, controller/backend reply with `нет активного визита`.
4. The operator has to hop between `Guests`, `Visits`, and `Taps` to understand which state is authoritative.

The audit goal was not to polish screens, but to establish whether the system still has a single domain truth for:

- guest identity;
- card ownership and operational use;
- visit lifecycle;
- pour lifecycle;
- tap authorization/runtime state.

High-level result:

- there is one canonical table per major entity;
- there is not one canonical cross-entity truth for the `guest <-> card <-> visit` relationship;
- the observed bug is not explainable as "projection stale only";
- actual model drift and duplicate/fantom relation paths are present.

## 2. Canonical domain model

### Guest

Canonical owner:

- `guests` table (`backend/models.py`)

Canonical fields:

- `guest_id`
- identity fields
- `balance`
- `is_active`

Source-of-truth notes:

- `Guest` is canonical for identity and balance.
- Guest API read models (`GET /api/guests`, `GET /api/guests/{id}`) are backend rows with joined `cards`.
- UI guest cards are therefore ownership-oriented read models, not visit-oriented read models.

UI/backend difference:

- guest UI usually treats `guest.cards[0]` as the visible/primary card;
- backend does not enforce one-card-per-guest or a single explicit `primary_card_uid`.

### Card

Canonical owner:

- `cards` table

Canonical fields:

- `card_uid`
- `guest_id`
- `status`

Source-of-truth notes:

- `cards.guest_id` is the canonical ownership/binding relation.
- It is not the canonical "active tap authorization" relation.
- There is no single canonical normalized representation of `card_uid` on write.

Critical domain split:

- `cards.guest_id` answers "whose card is this?"
- `visits.card_uid` answers "which card can authorize this active visit?"

This split is the main reason the same card can look valid in Guest UI but still be unusable on the tap.

Lost-card state:

- operationally canonical lost-card state lives in `lost_cards`;
- `cards.status == "lost"` is still read in some projections, but no active write path was found that sets it.

### Visit

Canonical owner:

- `visits` table

Canonical fields:

- `visit_id`
- `guest_id`
- `card_uid` (nullable since M3.5)
- `status`
- `active_tap_id`
- `lock_set_at`
- `closed_at`
- `card_returned`

Source-of-truth notes:

- `Visit` is the canonical active service context.
- `guest_id` is mandatory.
- `card_uid` is optional in the current model because migration `0003_m35_open_visit_without_card` made it nullable.
- Controller authorization uses `visits.card_uid`, not `cards.guest_id`.
- Tap lock truth lives in `Visit.active_tap_id` and `Visit.lock_set_at`.

Important implication:

- a visit may be valid and active while remaining intentionally or accidentally cardless;
- controller will still deny card authorization if `visits.card_uid` is null.

### Pour

Canonical owner:

- `pours` table

Canonical fields:

- `pour_id`
- `visit_id`
- `guest_id`
- `card_uid`
- `tap_id`
- `volume_ml`
- `amount_charged`
- `sync_status`

Source-of-truth notes:

- `Pour` is the canonical sale/pour record inside a visit flow.
- Authorization creates or reuses a `pending_sync` placeholder pour.
- Controller sync finalizes that pending pour into `synced` or another terminal state.

Non-sale side path:

- controller flow anomalies are not stored as `Pour`;
- they go into `non_sale_flows`;
- operator pour journal later heuristically matches `non_sale_flows` back to visits using `card_uid`, `short_id`, and time windows.

There is therefore no single "pour/session" persistence model. There is a sale path (`pours`) and an anomaly path (`non_sale_flows`).

### Tap

Canonical owner:

- `taps` table for tap inventory/config state
- `visits.active_tap_id` for active authorization lock

Canonical fields:

- `Tap.status`
- `Visit.active_tap_id`
- `Visit.lock_set_at`

Source-of-truth notes:

- tap service/config truth is in `taps`;
- active lock truth is in `visits`;
- controller runtime additionally keeps its own local runtime phase;
- display snapshot is derived from tap config plus some backend state, not from full visit/card context.

Display/runtime nuance:

- `display_crud.build_display_snapshot()` includes tap assignment, price, theme, and service flags;
- it does not include guest, card, or visit payload;
- `_resolve_display_tap_status()` may rewrite `processing_sync` to `active` when an active visit lock exists on that tap.

Conclusion for the canonical model:

- one canonical storage table exists per entity;
- no single canonical relationship model exists across `Guest`, `Card`, and `Visit`;
- "card attached to guest" and "card attached to active visit" are different truths in the current system.

## 3. Source-of-truth mapping

### Single source of truth matrix

| Entity | Canonical owner | Primary write path | Primary read paths | Dependent screens / behavior | Audit note |
|---|---|---|---|---|---|
| Guest | `guests` | `guest_crud.create_guest`, `guest_crud.update_guest`, `transaction_crud` for balance | `GET /api/guests`, `GET /api/guests/{id}`, joins in visit/operator read models | Guests, Visits, CardsGuests, Taps, controller balance checks | Canonical for identity and balance |
| Card | `cards` | `POST /api/guests/{guest_id}/cards`, `visit_crud.assign_card_to_active_visit`, `visit_crud.open_visit(card_uid=...)`, `visit_crud.close_visit` | guest lists/details, card lookup, visit open validation, operator search | Guest card chip, CardsGuests, reissue, visit card display | Canonical for card row and ownership, not for active authorization |
| Visit | `visits` | `POST /api/visits/open`, `POST /api/visits/{id}/assign-card`, `POST /api/visits/authorize-pour`, `POST /api/visits/{id}/close` | `GET /api/visits/active`, by-guest search, session history, operator tap workspace, card lookup active visit | Visits, Taps, controller auth, tap drawer | Canonical for active service context and tap lock |
| Pour | `pours` | `authorize-pour` creates `pending_sync`, `/api/sync/pours` finalizes, reconcile updates | pour list, session history, operator journals, KPI | Pours, session history, reports, today feed | Canonical sale record path |
| Tap | `taps` | tap assignment/config APIs, authorize/sync transitions | operator tap workspace, display snapshot, controller runtime checks | Taps, display bootstrap | Canonical tap device/config state, but lock lives on `Visit` |
| Lost card | `lost_cards` | `POST /api/visits/{id}/report-lost-card`, `POST /api/lost-cards/{uid}/restore` | `card_crud.resolve_card`, `authorize_pour_lock`, lost cards list | LostCards, CardsGuests, controller deny path | Canonical lost-card registry, not `cards.status` |
| Non-sale flow | `non_sale_flows` | controller `/api/controllers/flow-events` | operator pour journal, incident aggregation, tap history | operator feed, incidents | Separate anomaly path, later matched back to visits heuristically |

### Scenario mapping

| Scenario | Who writes | Where it writes | Who reads | What must update | Audit result |
|---|---|---|---|---|---|
| Create guest | Admin App `guestStore.createGuest` -> `POST /api/guests` | `guests` row | guest lists/details, operator search joins | `guests` only | Consistent |
| Bind card to guest | `guestStore.bindCardToGuest` -> `POST /api/guests/{guest}/cards` | `cards.guest_id`, `cards.status="inactive"` | Guests UI, card lookup guest payload | `cards` only | Consistent for ownership only; does not update `Visit` |
| Replace / reissue card | CardsGuests flow: `bindCardToGuest`, then optionally `assignCardToVisit` | new/updated `cards` row, then `visits.card_uid` if target visit exists | Guests, Visits, card lookup, controller | both `cards` and `visits` if active visit should continue | Implemented as two separate, non-atomic writes |
| Open visit | `visitStore.openVisit` -> `POST /api/visits/open` | new `visits` row, optionally `visits.card_uid`, maybe `cards.status="active"` | Visits, operator taps, controller auth | `visits` always; `cards` only if `card_uid` passed | Current UI often opens cardless visit even when guest already has card |
| Recharge / top-up | `guestStore.topUpBalance` -> `POST /api/guests/{guest}/topup` | `transactions`, `guests.balance`, optional `transactions.visit_id` by active guest visit | Guests, visit list balance, controller auth balance checks | `guests.balance`, `transactions` | Consistent; linked to active visit by `guest_id`, not by card |
| Authorize on tap | controller -> `POST /api/visits/authorize-pour` | `visits.active_tap_id`, `visits.lock_set_at`, `taps.status="processing_sync"`, `pours(sync_status="pending_sync")` | controller runtime, tap drawer, operator taps, later sync | `Visit`, `Tap`, pending `Pour` | Depends only on active visit by `visits.card_uid`; fails for cardless visit or UID case mismatch |
| Finish pour / sync | controller -> `POST /api/sync/pours` | updates pending `Pour` to `synced` or rejected; decrements `guests.balance`; decrements `kegs.current_volume_ml`; clears visit lock | Pours, session history, KPI, taps | `Pour`, `Guest.balance`, `Keg`, `Visit.active_tap_id`, `Tap.status` | Consistent when pending authorize exists |
| Close visit | `visitStore.closeVisit` -> `POST /api/visits/{id}/close` | `visits.status`, `closed_at`, `card_returned`, clears lock; `cards.status="inactive"`; maybe `cards.guest_id=null` if returned | Visits, Guests, future bind/open flows | `Visit`, `Card`, lock state | Consistent with current split model |
| Lost / restore / reissue | `report-lost-card`, `restore_lost_card`, then reissue UI writes `cards` and maybe `visits` | `lost_cards`, then `cards`, then optionally `visits` | card lookup, controller auth, lost-card screens | `lost_cards` always; `visits` only if reissue assigns new card to active visit | Lost state is canonical in registry; reissue is multi-step and non-atomic |

## 4. UI/backend/controller/display consistency review

### What is aligned

- `Guest` identity and balance are consistently read from backend `Guest`.
- `Visit` lock and active-tap context are consistently read from backend `Visit`.
- `authorize-pour` and `/api/sync/pours` agree on the use of `Visit.active_tap_id`, pending sync pours, and tap lock clearing.
- Lost-card denial consistently uses `lost_cards` in backend and controller authorize flow.

### What is not aligned

| Layer | Reads from | What it thinks is true | Consistency verdict |
|---|---|---|---|
| Guest screen | `GET /api/guests`, `guest.cards[0]` | "Guest has card" | Ownership truth only |
| Visit screen | `GET /api/visits/active`, `visit.card_uid` | "Visit has/no card" | Active-visit truth only |
| Card lookup / CardsGuests | `card_crud.resolve_card()` hybrid payload | mixes guest ownership, active visit, and lost-card registry | Hybrid projection, not a single truth |
| Operator tap workspace | `visit_crud.get_active_visits_list()` | active session card comes from `visit.card_uid` | Visit truth only |
| Controller authorize flow | `lost_cards` + `visits.card_uid` + exact match | card is valid only if active visit exists for that card UID | Different from Guest screen |
| Tap display bootstrap | display snapshot derived from `Tap` config/state | does not know guest/card/visit context | Cannot independently validate visit/card truth |
| Tap display runtime | controller runtime payload | shows denied/authorized states from controller | Inherits controller truth, not Guest screen truth |

Direct answers to the audit questions:

- Guest screen does not look at the same relation as Visit screen.
- Visit screen is not merely stale by default; it is reading a different canonical field.
- Controller does not authorize against the same relation that Guest UI displays.
- Old "session" vocabulary still exists in UI/operator/controller internals and increases ambiguity.
- There are multiple parallel card-link representations.

## 5. Reproduced broken scenario

Reproduced target scenario:

1. open guest;
2. bind card to guest;
3. guest card shows the card;
4. open or inspect visit;
5. visit still shows `Без карты`;
6. use card on tap;
7. backend/controller reply with `no_active_visit`.

### Scenario A: bind card to guest, then open visit without card

Observed API trace:

| Step | Action | Observed result |
|---|---|---|
| 1 | `POST /api/guests/{guest_id}/cards` with `CARD-A-30001` | guest response contains `cards[0].card_uid="CARD-A-30001"` and card `status="inactive"` |
| 2 | `POST /api/visits/open` with only `guest_id` | visit created successfully with `"card_uid": null` |
| 3 | `GET /api/visits/active/by-guest/{guest_id}` | returns the same active visit with `"card_uid": null` |
| 4 | `GET /api/cards/CARD-A-30001/resolve` | returns `guest != null`, `card != null`, `active_visit = null`, `recommended_action = "open_new_visit"` |
| 5 | `POST /api/visits/authorize-pour` with `{card_uid: CARD-A-30001, tap_id}` | `409 {"detail":{"reason":"no_active_visit","message":"No active visit for Card ..."}}` |

Conclusion:

- the card bind updated card ownership only;
- the visit remained cardless;
- controller denial is correct according to current backend model;
- this is not fixed by forcing a UI refresh, because the visit row itself never changed.

### Scenario B: open cardless visit first, then bind card to guest

Observed result:

- exactly the same backend end state;
- active visit remains `card_uid = null`;
- card resolve still shows `guest` but no `active_visit`;
- authorize still returns `no_active_visit`.

Conclusion:

- bind-card mutation does not backfill an already-open active visit.

### Scenario C: control run with visit explicitly opened using card

Observed result:

- opening visit with `card_uid` present does create an active visit usable by authorize flow;
- authorize succeeds when request `card_uid` matches stored `visits.card_uid` exactly;
- authorize fails with `no_active_visit` when controller-style lowercased UID is sent against an uppercase stored visit card.

Concrete control evidence:

- stored uppercase card UID: authorize with uppercase -> `200 allowed=true`
- same stored uppercase card UID: authorize with lowercase -> `409 no_active_visit`
- stored lowercase card UID: authorize with lowercase -> `200 allowed=true`

Conclusion:

- there is a second independent bug in the controller/backend contract: case normalization mismatch.

### Scenario D: duplicate physical card identity by case variant

Observed result:

- guest 1 bound `CASE-DUP`
- guest 2 bound `case-dup`
- both requests returned `200`
- `GET /api/cards/case-dup/resolve` returned the first case-insensitive match (`CASE-DUP`) and guest 1, ignoring the second exact-case row

Conclusion:

- the system currently allows duplicate card rows for the same physical UID if case differs;
- some read paths are case-insensitive and return an arbitrary first match;
- this is a real duplicate/fantom entity path.

## 6. Identified mismatches

| # | Mismatch | Class | Evidence | Impact |
|---|---|---|---|---|
| 1 | `cards.guest_id` and `visits.card_uid` are parallel truths for card relation | Model drift / duplicated relation | guest bind updates only `Card`; controller authorize reads only `Visit` | Main cause of "card visible on guest, no card on visit, no active visit on tap" |
| 2 | Guest, Visits, and CardsGuests routes commonly open visits without passing card UID | Workflow/domain mismatch | `Guests.svelte`, `Visits.svelte`, `CardsGuests.svelte` call `openVisit({ guestId })` | Creates cardless active visits even for guests who already have cards |
| 3 | Binding a card to a guest does not update an active visit | Missing domain transition | reproduced both before-open and after-open variants | Refresh alone cannot fix the observed state |
| 4 | Controller lowercases `card_uid`, while `authorize-pour` active-visit lookup is exact/case-sensitive | Contract bug | controller runtime uses lowercase; `visit_crud.get_active_visit_by_card_uid()` is exact match | A correctly linked visit can still be rejected as `no_active_visit` |
| 5 | Card write paths are case-sensitive, while several read paths are case-insensitive | Duplicate/fantom entity path | `CASE-DUP` and `case-dup` can both exist; resolve returns first match | Same physical card can exist twice and resolve to the wrong guest |
| 6 | Guest can have multiple cards, while UI often treats `guest.cards[0]` as the primary card | Missing invariant / phantom primary-card representation | no unique constraint on `cards.guest_id`; binding two cards to same guest reproduced successfully | UI may show an arbitrary first card as the canonical one |
| 7 | Lost-card state is canonical in `lost_cards`, but projections also read `card.status == "lost"` | Split representation / legacy residue | no active write path found for `cards.status="lost"`; operator search still reads it | Lost-card truth can drift across projections |
| 8 | `guest_crud.assign_card_to_guest()` still exists and sets `card.status="active"`, unlike the active bind path which sets `"inactive"` | Dead legacy path / conflicting contract | duplicate helper in backend | Future reuse would reintroduce inconsistent semantics |
| 9 | UI/operator/controller still mix `visit` and `session` language and contracts | Conceptual drift | session history/store names, controller `session_state`, `non_sale_flows` matching | Raises cognitive overhead and hides which state is canonical |
| 10 | Display snapshot does not include visit/card context, while runtime denial comes from controller auth | Layer split | display bootstrap is tap/config only; runtime denial inherits controller result | Display and Guest UI can diverge even when both are "correct" by their own source |

Which mismatches are root cause vs amplifiers:

- root cause for the observed bug: items 1, 2, and 3;
- severe independent contract bug: items 4 and 5;
- latent but real domain drift risks: items 6 through 10.

## 7. Invariants

The following should be treated as required product/system invariants.

### Identity and normalization invariants

1. `card_uid` must have one canonical normalized form at write time.
2. The system must not allow two `Card` rows that differ only by case.
3. All read paths, join paths, and controller paths must compare `card_uid` using the same normalization rule.

### Guest/card invariants

4. The product must explicitly decide whether one guest may own multiple cards.
5. If multiple cards are allowed, UI must not treat `guest.cards[0]` as an implicit canonical card.
6. If only one card is allowed, that must be enforced in backend invariants and migration constraints.

### Visit/card invariants

7. `Visit.guest_id` is mandatory for every visit.
8. If the product wants a guest-bound card to authorize the current visit, `Visit.card_uid` must be updated explicitly and atomically.
9. If a visit is intentionally cardless, UI must present it as cardless and must not imply that a guest-bound card will work on the tap.
10. Controller authorization must depend on the same normalized visit-card relation that Admin App presents as tap-usable.
11. There must be at most one active visit per guest.
12. There must be at most one active visit per normalized card UID.

### Tap/runtime invariants

13. The active-tap lock truth must remain `Visit.active_tap_id` plus `Visit.lock_set_at`.
14. Display/runtime messaging about "active session" should never imply a different authorization context than controller/backend use.

### Lost-card invariants

15. Lost-card truth must live in one canonical representation.
16. If `lost_cards` is canonical, projections must stop interpreting `cards.status == "lost"` as an alternative truth.

### Allowed vs violating states

Allowed state:

- guest has a bound card;
- guest has no active visit;
- card lookup recommends opening a new visit.

Conditionally allowed state:

- guest has a bound card;
- active visit exists with `visit.card_uid = null`;
- this is only valid if the product intentionally supports a cardless visit and the UI clearly communicates that the bound guest card is not attached to that visit.

Consistency violation:

- guest screen implies the card is ready for the current visit;
- visit remains cardless;
- controller still authorizes only by `visit.card_uid`.

Hard violation:

- two card rows differ only by UID case;
- any layer resolves them inconsistently.

## 8. Recommended fix strategy

### Fix first

1. Decide the canonical service-card rule.

Choose one explicit product rule:

- Rule A: a guest-bound primary card should automatically become the current active visit card.
- Rule B: guest ownership and visit authorization stay separate, but UI must treat them as separate and require an explicit "attach card to visit" step.

Without that decision, every local fix will keep drifting.

2. Normalize `card_uid` everywhere.

Immediate high-confidence work:

- normalize `card_uid` on all writes;
- normalize `card_uid` on all comparisons;
- add migration/backfill for existing mixed-case rows;
- add uniqueness over normalized UID, not raw string only.

This is mandatory because the controller already lowercases card UIDs.

### Local fixes that are valid even before bigger consolidation

1. Stop opening cardless visits from Guest/Card workflows when the operator intent is clearly "this guest is using this card now".
2. If the product keeps separate ownership and visit attachment, make the UI label that explicit:
   - `Bound card`
   - `Visit card`
3. Remove `guest.cards[0]` as an implicit primary-card contract unless backend enforces it.

These are containment fixes, not final consolidation.

### Domain consolidation work

1. Introduce one explicit domain command for active-card attachment.

Examples:

- `open_visit_with_card(guest_id, card_uid)`
- `attach_card_to_active_visit(guest_id, visit_id, card_uid)`
- `reissue_active_visit_card(visit_id, old_uid, new_uid)`

That command should atomically manage:

- card ownership/binding rules;
- active visit card relation;
- card status transitions;
- invalidation events for affected read models.

2. Remove dead/duplicate contracts.

Candidates:

- `guest_crud.assign_card_to_guest()` legacy helper;
- `cards.status == "lost"` as a parallel lost-state truth;
- any read path that depends on `guest.cards[0]` as a hidden canonical card.

3. Make session vocabulary explicit.

- If `Visit` is the canonical entity, operator/frontend should stop hiding that behind mixed `session` semantics where it changes the meaning.
- Controller `session_state` should be documented as runtime telemetry, not as a competing persistence model.

### Migration / cleanup work

1. Backfill and deduplicate case-variant cards.
2. Decide and enforce one-card-per-guest or add an explicit `primary_card_uid`.
3. Clean projections and stores so each screen clearly declares whether it is showing:
   - guest ownership state;
   - active visit service-card state;
   - controller runtime state;
   - display bootstrap state.

## 9. Final verdict

Final verdict:

`MODEL DRIFT DETECTED, CONSOLIDATION NEEDED`

Why:

- there is one canonical table per entity, but not one canonical source of truth for the guest/card/visit relationship;
- duplicate/fantom card paths are real, not hypothetical;
- the known bug is caused by actual domain split plus workflow mistakes, not by a mere projection refresh miss;
- controller/backend UID normalization mismatch is a separate production-risk bug that can break even otherwise correct visit-card links.

Short audit summary:

- Guest ownership truth lives in `cards.guest_id`.
- Visit authorization truth lives in `visits.card_uid`.
- Controller trusts the second one only.
- Guest UI often shows the first one.
- Current workflows frequently fail to keep them aligned.
