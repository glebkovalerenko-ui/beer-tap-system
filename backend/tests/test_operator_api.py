from datetime import date, datetime, timezone
from decimal import Decimal

import models


def _auth_headers(client, username: str = "operator") -> dict[str, str]:
    response = client.post(
        "/api/token",
        data={"username": username, "password": "fake_password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_operator_fixture(db_session):
    now = datetime.now(timezone.utc)

    beverage = models.Beverage(
        name="Operator Lager",
        brewery="Demo Brewery",
        style="Lager",
        abv=Decimal("4.80"),
        sell_price_per_liter=Decimal("700.00"),
    )
    keg = models.Keg(
        beverage=beverage,
        initial_volume_ml=50000,
        current_volume_ml=45500,
        purchase_price=Decimal("12000.00"),
        status="in_use",
    )
    tap_active = models.Tap(
        tap_id=1,
        display_name="Tap 1",
        status="active",
        keg=keg,
    )
    tap_active.display_config = models.TapDisplayConfig(enabled=True)

    tap_idle = models.Tap(
        tap_id=2,
        display_name="Tap 2",
        status="locked",
    )
    tap_idle.display_config = models.TapDisplayConfig(enabled=False)

    guest = models.Guest(
        last_name="Ivanov",
        first_name="Ivan",
        patronymic="Ivanovich",
        phone_number="+79990001122",
        date_of_birth=date(1990, 1, 1),
        id_document="4510 123456",
        balance=Decimal("1200.00"),
        is_active=True,
    )
    card = models.Card(
        card_uid="04AB7815CD6B80",
        guest=guest,
        status="active",
    )
    visit = models.Visit(
        guest=guest,
        card=card,
        card_uid=card.card_uid,
        status="active",
        active_tap_id=1,
        lock_set_at=now,
        card_returned=False,
    )
    shift = models.Shift(status="open", opened_by="operator")
    controller = models.Controller(
        controller_id="controller-1",
        ip_address="10.0.0.21",
        firmware_version="1.0.0",
        last_seen=now,
    )
    top_up = models.Transaction(
        guest=guest,
        amount=Decimal("500.00"),
        type="top-up",
        payment_method="cash",
        created_at=now,
    )
    synced_pour = models.Pour(
        client_tx_id="operator-sync-1",
        guest=guest,
        card=card,
        card_uid=card.card_uid,
        visit=visit,
        tap=tap_active,
        keg=keg,
        volume_ml=500,
        amount_charged=Decimal("350.00"),
        price_per_ml_at_pour=Decimal("0.7000"),
        duration_ms=5000,
        sync_status="synced",
        poured_at=now,
        authorized_at=now,
        synced_at=now,
        short_id="ABC123",
    )
    pending_pour = models.Pour(
        client_tx_id="operator-pending-1",
        guest=guest,
        card=card,
        card_uid=card.card_uid,
        visit=visit,
        tap=tap_active,
        keg=keg,
        volume_ml=0,
        amount_charged=Decimal("0.00"),
        price_per_ml_at_pour=Decimal("0.7000"),
        duration_ms=None,
        sync_status="pending_sync",
        poured_at=now,
        authorized_at=now,
    )

    db_session.add_all(
        [
            beverage,
            keg,
            tap_active,
            tap_idle,
            guest,
            card,
            visit,
            shift,
            controller,
            top_up,
            synced_pour,
            pending_pour,
        ]
    )
    db_session.commit()


def test_operator_today_returns_projection_bundle(client, db_session):
    _seed_operator_fixture(db_session)

    response = client.get("/api/operator/today", headers=_auth_headers(client, "operator"))
    assert response.status_code == 200

    payload = response.json()
    assert payload["current_shift"]["status"] == "open"
    assert payload["today_summary"]["sessions_count"] == 1
    assert payload["feed_items"]
    assert any(item["kind"] == "no_keg" for item in payload["attention_items"])
    assert payload["priority_cta_source"]


def test_operator_taps_returns_enriched_workspace_and_detail(client, db_session):
    _seed_operator_fixture(db_session)
    headers = _auth_headers(client, "shift_lead")

    response = client.get("/api/operator/taps", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    tap_one = next(item for item in payload if item["tap_id"] == 1)
    assert tap_one["active_session"]["guest_full_name"] == "Ivanov Ivan Ivanovich"
    assert tap_one["sync_state"] == "syncing"
    assert tap_one["safe_actions"]["keg"]["allowed"] is True
    assert tap_one["safe_actions"]["screen"]["allowed"] is False
    assert tap_one["recent_events"]

    detail_response = client.get("/api/operator/taps/1", headers=headers)
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["tap_id"] == 1
    assert detail_payload["history_items"]


def test_operator_card_lookup_returns_context_summary_and_recent_events(client, db_session):
    _seed_operator_fixture(db_session)

    response = client.get(
        "/api/operator/cards/lookup",
        params={"query": "04AB7815CD6B80"},
        headers=_auth_headers(client, "operator"),
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["recommended_action"] == "open_active_visit"
    assert payload["last_tap_label"] == "Tap 1"
    assert any(item["key"] == "balance" for item in payload["lookup_summary_items"])
    assert len(payload["recent_events"]) >= 2
    assert "open-history" in payload["allowed_quick_actions"]
    assert "top-up" not in payload["allowed_quick_actions"]
