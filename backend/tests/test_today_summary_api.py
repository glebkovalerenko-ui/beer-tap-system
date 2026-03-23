from datetime import datetime, timedelta, timezone
from decimal import Decimal

import models


def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_today_summary_uses_shift_aggregate_window(client, db_session):
    headers = _login(client)
    open_shift = models.Shift(status="open", opened_at=datetime.now(timezone.utc) - timedelta(hours=2))
    db_session.add(open_shift)

    guest = models.Guest(
        last_name="Summary",
        first_name="Tester",
        patronymic=None,
        phone_number="+70000000001",
        date_of_birth=datetime(1990, 1, 1).date(),
        id_document="SUM-1",
        balance=Decimal("1000.00"),
        is_active=True,
    )
    card = models.Card(card_uid="SUM-CARD", guest=guest, status="active")
    tap = models.Tap(tap_id=77, display_name="Summary Tap", status="active")
    keg = models.Keg(initial_volume_ml=5000, current_volume_ml=4500, purchase_price=Decimal("1000.00"), status="in_use")
    tap.keg = keg
    visit = models.Visit(guest=guest, card=card, status="closed", opened_at=datetime.now(timezone.utc) - timedelta(hours=1))

    recent_pour = models.Pour(
        client_tx_id="sum-recent", guest=guest, card=card, visit=visit, tap=tap, keg=keg,
        volume_ml=350, amount_charged=Decimal("122.50"), price_per_ml_at_pour=Decimal("0.3500"),
        sync_status="synced", short_id="SUM1234", poured_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        synced_at=datetime.now(timezone.utc) - timedelta(minutes=29),
    )
    old_pour = models.Pour(
        client_tx_id="sum-old", guest=guest, card=card, visit=visit, tap=tap, keg=keg,
        volume_ml=999, amount_charged=Decimal("999.00"), price_per_ml_at_pour=Decimal("1.0000"),
        sync_status="synced", short_id="SUM5678", poured_at=datetime.now(timezone.utc) - timedelta(days=1),
        synced_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    pending_pour = models.Pour(
        client_tx_id="sum-pending", guest=guest, card=card, visit=visit, tap=tap, keg=keg,
        volume_ml=200, amount_charged=Decimal("70.00"), price_per_ml_at_pour=Decimal("0.3500"),
        sync_status="pending_sync", short_id="SUM9999", poured_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )

    db_session.add_all([guest, card, tap, keg, visit, recent_pour, old_pour, pending_pour])
    db_session.commit()

    response = client.get("/api/pours/today-summary", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "shift"
    assert payload["sessions_count"] == 1
    assert payload["volume_ml"] == 350
    assert payload["revenue"] == 122.5
    assert payload["summary_complete"] is False
    assert "ожидании синхронизации" in payload["fallback_copy"]
