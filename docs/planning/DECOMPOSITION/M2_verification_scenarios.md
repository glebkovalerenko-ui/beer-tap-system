# M2 Verification Scenarios (Pilot-ready, demo-oriented)

## Primary demo flow
1. Register guest (18+).
2. Bind card to guest.
3. Open visit (`status=active`, card becomes `active`).
4. Top-up guest balance.
5. Lookup active visit by card.
6. Perform pour sync (accepted only with active visit).
7. Close visit (`status=closed`, card becomes `inactive`).
8. Attempt pour with same card after close -> rejected.

## Additional required scenarios
9. Attempt second active visit for same guest -> `409`.
10. Attempt second active visit for same card -> `409`.
11. Top-up without active visit -> allowed (`200`).
12. Close visit with `card_returned=false` -> persisted in visit record.

## TODO/Explicit defer
- Automatic card deactivation by timeout is deferred; no timer-based rule in M2.
