# M6 Verification: LostCard Resolve + NFC Lookup

## Preconditions
- Backend is running with latest migrations.
- Admin app is built and connected to local backend.
- NFC reader is available and card scanning works in existing `NFCModal`.

## Verification Steps
1. Open `Visits` page and click `Найти по карте (NFC)`.
2. Scan a card from an active visit.
3. Confirm result block shows `Карта используется в активном визите` and button `Открыть карточку визита`.
4. Mark the same card as lost (from visit actions), then scan again via `Найти по карте (NFC)`.
5. Confirm result block shows `Карта отмечена как потерянная`, then click `Снять отметку потерянной`.
6. Go to `Потерянные карты`, click `Найти по карте (NFC)`, and scan:
   - one lost card,
   - one guest-bound card without active visit,
   - one unknown card.
7. Confirm statuses are shown correctly:
   - lost card,
   - bound with no active visit,
   - unknown card.
8. For unknown card, confirm no unsafe action buttons are shown by default.

## Backend Test Coverage
- `backend/tests/test_m6_lost_cards.py` includes resolve cases:
  - lost card,
  - active visit card,
  - guest-bound no active visit,
  - unknown card.
