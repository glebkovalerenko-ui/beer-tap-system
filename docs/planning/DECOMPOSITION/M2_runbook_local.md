# M2 Local Runbook (Visit Model + Invariants)

## 1. Apply migrations
```bash
cd backend
alembic upgrade head
```

## 2. Run backend tests (M2-focused)
```bash
cd backend
pytest tests/test_visit_invariants.py tests/test_business_lifecycles.py
```

## 3. Start backend
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Demo flow (recommended)
1. Register guest (18+).
2. Bind/assign card to guest.
3. Open visit with guest + card.
4. Top-up guest balance.
5. Simulate pour sync using card.
6. Close visit.
7. Verify same card is rejected for pour without active visit.

## 5. Additional scenario
- Top-up without active visit must still succeed (balance is global on guest).
