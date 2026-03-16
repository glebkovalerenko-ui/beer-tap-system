import json
import uuid
from datetime import date
from decimal import Decimal

import models


def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_tap_with_keg(db_session, *, tap_id: int = 7, current_volume_ml: int = 5000):
    beverage = models.Beverage(
        name=f"Test Beverage {tap_id}",
        brewery="Test Brewery",
        style="Lager",
        abv=Decimal("5.0"),
        sell_price_per_liter=Decimal("350.00"),
    )
    keg = models.Keg(
        beverage=beverage,
        initial_volume_ml=current_volume_ml,
        current_volume_ml=current_volume_ml,
        purchase_price=Decimal("2000.00"),
        status="in_use",
    )
    tap = models.Tap(
        tap_id=tap_id,
        display_name=f"Tap {tap_id}",
        status="active",
        keg=keg,
    )
    db_session.add_all([beverage, keg, tap])
    db_session.commit()
    return tap, keg


def _create_sale_pour(db_session, *, tap_id: int, keg_id, volume_ml: int):
    guest = models.Guest(
        last_name="Tester",
        first_name="Sale",
        patronymic=None,
        phone_number=f"+7000000{tap_id:04d}",
        date_of_birth=date(1990, 1, 1),
        id_document=f"SALE-{tap_id}",
        balance=Decimal("1000.00"),
        is_active=True,
    )
    card = models.Card(card_uid=f"CARD-{tap_id}", guest=guest, status="active")
    visit = models.Visit(guest=guest, card=card, status="closed")
    pour = models.Pour(
        client_tx_id=f"sale-{tap_id}-{volume_ml}",
        guest=guest,
        card=card,
        visit=visit,
        tap_id=tap_id,
        keg_id=keg_id,
        volume_ml=volume_ml,
        amount_charged=Decimal("70.00"),
        price_per_ml_at_pour=Decimal("0.3500"),
        duration_ms=1200,
        sync_status="synced",
        short_id="SALE1234",
    )
    db_session.add_all([guest, card, visit, pour])
    db_session.commit()
    return pour


def _login_and_open_shift(client):
    headers = _login(client)
    response = client.post("/api/shifts/open", headers=headers)
    assert response.status_code in {200, 409}
    return headers


def _create_active_visit_with_tap(
    client,
    *,
    suffix: str,
    card_uid: str,
    sell_price_per_liter: float = 350.0,
    topup_amount: float = 500.0,
    initial_volume_ml: int = 5000,
):
    headers = _login_and_open_shift(client)
    guest_response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Flow{suffix}",
            "first_name": "Tester",
            "patronymic": "Closure",
            "phone_number": f"+1888000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"FLOW-{suffix}",
        },
    )
    assert guest_response.status_code == 201
    guest_id = guest_response.json()["guest_id"]

    card_response = client.post(
        f"/api/guests/{guest_id}/cards",
        headers=headers,
        json={"card_uid": card_uid},
    )
    assert card_response.status_code == 200

    beverage_response = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": f"Flow Beer {suffix}", "sell_price_per_liter": sell_price_per_liter},
    )
    assert beverage_response.status_code == 201
    beverage_id = beverage_response.json()["beverage_id"]

    keg_response = client.post(
        "/api/kegs/",
        headers=headers,
        json={
            "beverage_id": beverage_id,
            "initial_volume_ml": initial_volume_ml,
            "purchase_price": 1000.0,
        },
    )
    assert keg_response.status_code == 201
    keg_id = keg_response.json()["keg_id"]

    tap_response = client.post(
        "/api/taps/",
        headers=headers,
        json={"display_name": f"Flow Tap {suffix}"},
    )
    assert tap_response.status_code == 201
    tap_id = tap_response.json()["tap_id"]

    assign_response = client.put(
        f"/api/taps/{tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_id},
    )
    assert assign_response.status_code == 200

    topup_response = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": topup_amount, "payment_method": "cash"},
    )
    assert topup_response.status_code == 200

    visit_response = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert visit_response.status_code == 200

    return {
        "headers": headers,
        "guest_id": guest_id,
        "visit_id": visit_response.json()["visit_id"],
        "tap_id": tap_id,
        "keg_id": uuid.UUID(keg_id),
        "card_uid": card_uid,
        "initial_volume_ml": initial_volume_ml,
    }


def _register_pending_pour(client, *, card_uid: str, tap_id: int, client_tx_id: str, short_id: str, volume_ml: int, duration_ms: int, price_per_ml_at_pour: str):
    response = client.post(
        "/api/visits/register-pending-pour",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "client_tx_id": client_tx_id,
            "short_id": short_id,
            "card_uid": card_uid,
            "tap_id": tap_id,
            "duration_ms": duration_ms,
            "volume_ml": volume_ml,
            "price_per_ml_at_pour": price_per_ml_at_pour,
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    return response


def test_controller_flow_event_is_written_to_audit_log(client, db_session):
    _create_tap_with_keg(db_session, tap_id=7)

    response = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "event_id": "tap-7-closed-1",
            "event_status": "started",
            "tap_id": 7,
            "volume_ml": 12,
            "duration_ms": 1400,
            "card_present": False,
            "valve_open": False,
            "session_state": "no_card_no_session",
            "card_uid": None,
            "short_id": None,
            "reason": "flow_detected_when_valve_closed_without_active_session",
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True

    audit = (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "controller_flow_event", models.AuditLog.target_id == "7")
        .one()
    )
    details = json.loads(audit.details)
    assert details["event_id"] == "tap-7-closed-1"
    assert details["event_status"] == "started"
    assert details["tap_id"] == 7
    assert details["volume_ml"] == 12
    assert details["session_state"] == "no_card_no_session"

    non_sale_flow = (
        db_session.query(models.NonSaleFlow)
        .filter(models.NonSaleFlow.event_id == "tap-7-closed-1")
        .one()
    )
    assert non_sale_flow.volume_ml == 12
    assert non_sale_flow.flow_category == "closed_valve_no_card"

    keg = db_session.query(models.Keg).filter(models.Keg.keg_id == non_sale_flow.keg_id).one()
    assert keg.current_volume_ml == 4988


def test_live_feed_returns_latest_snapshot_per_flow_event(client, db_session):
    headers = _login(client)
    _create_tap_with_keg(db_session, tap_id=3)

    first = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "event_id": "tap-3-auth-1",
            "event_status": "started",
            "tap_id": 3,
            "volume_ml": 15,
            "duration_ms": 1000,
            "card_present": True,
            "valve_open": True,
            "session_state": "authorized_session",
            "card_uid": "CARD-123",
            "short_id": "ABC12345",
            "reason": "authorized_pour_in_progress",
        },
    )
    assert first.status_code == 202

    second = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "event_id": "tap-3-auth-1",
            "event_status": "updated",
            "tap_id": 3,
            "volume_ml": 37,
            "duration_ms": 2400,
            "card_present": True,
            "valve_open": True,
            "session_state": "authorized_session",
            "card_uid": "CARD-123",
            "short_id": "ABC12345",
            "reason": "authorized_pour_in_progress",
        },
    )
    assert second.status_code == 202

    feed = client.get("/api/pours/live-feed?limit=10", headers=headers)
    assert feed.status_code == 200

    item = next(entry for entry in feed.json() if entry["item_id"] == "tap-3-auth-1")
    assert item["item_type"] == "flow_event"
    assert item["event_status"] == "updated"
    assert item["status"] == "in_progress"
    assert item["volume_ml"] == 37
    assert item["session_state"] == "authorized_session"
    assert item["short_id"] == "ABC12345"


def test_authorized_sale_flow_creates_pour_and_skips_non_sale_accounting(client, db_session):
    setup = _create_active_visit_with_tap(client, suffix="97021", card_uid="CARD-FLOW-97021")

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=setup["headers"],
        json={"card_uid": setup["card_uid"], "tap_id": setup["tap_id"]},
    )
    assert authorize.status_code == 200

    event_headers = {"X-Internal-Token": "demo-secret-key"}
    for event_status, volume_ml, duration_ms, valve_open in [
        ("started", 120, 1400, True),
        ("updated", 280, 2600, True),
        ("stopped", 280, 3100, False),
    ]:
        response = client.post(
            "/api/controllers/flow-events",
            headers=event_headers,
            json={
                "event_id": "tap-sale-97021",
                "event_status": event_status,
                "tap_id": setup["tap_id"],
                "volume_ml": volume_ml,
                "duration_ms": duration_ms,
                "card_present": True,
                "valve_open": valve_open,
                "session_state": "authorized_session",
                "card_uid": setup["card_uid"],
                "short_id": "SALE7021",
                "reason": "authorized_pour_in_progress",
            },
        )
        assert response.status_code == 202

    assert db_session.query(models.NonSaleFlow).count() == 0
    _register_pending_pour(
        client,
        card_uid=setup["card_uid"],
        tap_id=setup["tap_id"],
        client_tx_id="sale-flow-sync-97021",
        short_id="SALE7021",
        volume_ml=280,
        duration_ms=3100,
        price_per_ml_at_pour="0.3500",
    )

    sync_response = client.post(
        "/api/sync/pours",
        headers=event_headers,
        json={
            "pours": [
                {
                    "client_tx_id": "sale-flow-sync-97021",
                    "card_uid": setup["card_uid"],
                    "tap_id": setup["tap_id"],
                    "short_id": "SALE7021",
                    "duration_ms": 3100,
                    "volume_ml": 280,
                    "tail_volume_ml": 0,
                    "price_cents": 9800,
                }
            ]
        },
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["results"][0]["status"] == "accepted"

    db_session.expire_all()
    pour = (
        db_session.query(models.Pour)
        .filter(models.Pour.visit_id == uuid.UUID(setup["visit_id"]), models.Pour.tap_id == setup["tap_id"])
        .one()
    )
    assert pour.sync_status == "synced"
    assert pour.volume_ml == 280
    assert db_session.query(models.NonSaleFlow).count() == 0

    keg = db_session.query(models.Keg).filter(models.Keg.keg_id == setup["keg_id"]).one()
    assert keg.current_volume_ml == setup["initial_volume_ml"] - 280


def test_authorized_tail_flow_stays_on_same_pour_and_does_not_create_non_sale_flow(client, db_session):
    setup = _create_active_visit_with_tap(client, suffix="97022", card_uid="CARD-FLOW-97022")

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=setup["headers"],
        json={"card_uid": setup["card_uid"], "tap_id": setup["tap_id"]},
    )
    assert authorize.status_code == 200

    event_headers = {"X-Internal-Token": "demo-secret-key"}
    for event_status, volume_ml, duration_ms, valve_open in [
        ("started", 250, 2000, True),
        ("updated", 315, 2800, True),
        ("stopped", 315, 3400, False),
    ]:
        response = client.post(
            "/api/controllers/flow-events",
            headers=event_headers,
            json={
                "event_id": "tap-tail-97022",
                "event_status": event_status,
                "tap_id": setup["tap_id"],
                "volume_ml": volume_ml,
                "duration_ms": duration_ms,
                "card_present": True,
                "valve_open": valve_open,
                "session_state": "authorized_session",
                "card_uid": setup["card_uid"],
                "short_id": "TAIL7022",
                "reason": "authorized_pour_in_progress",
            },
        )
        assert response.status_code == 202

    assert db_session.query(models.NonSaleFlow).count() == 0
    _register_pending_pour(
        client,
        card_uid=setup["card_uid"],
        tap_id=setup["tap_id"],
        client_tx_id="sale-tail-sync-97022",
        short_id="TAIL7022",
        volume_ml=315,
        duration_ms=3400,
        price_per_ml_at_pour="0.3500",
    )

    sync_response = client.post(
        "/api/sync/pours",
        headers=event_headers,
        json={
            "pours": [
                {
                    "client_tx_id": "sale-tail-sync-97022",
                    "card_uid": setup["card_uid"],
                    "tap_id": setup["tap_id"],
                    "short_id": "TAIL7022",
                    "duration_ms": 3400,
                    "volume_ml": 315,
                    "tail_volume_ml": 35,
                    "price_cents": 11025,
                }
            ]
        },
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["results"][0]["status"] == "accepted"

    db_session.expire_all()
    pours = (
        db_session.query(models.Pour)
        .filter(models.Pour.visit_id == uuid.UUID(setup["visit_id"]), models.Pour.tap_id == setup["tap_id"])
        .all()
    )
    assert len(pours) == 1
    assert pours[0].sync_status == "synced"
    assert pours[0].volume_ml == 315
    assert db_session.query(models.NonSaleFlow).count() == 0

    keg = db_session.query(models.Keg).filter(models.Keg.keg_id == setup["keg_id"]).one()
    assert keg.current_volume_ml == setup["initial_volume_ml"] - 315


def test_non_sale_flow_updates_keg_by_delta_and_keeps_guest_pours_empty(client, db_session):
    _, keg = _create_tap_with_keg(db_session, tap_id=5, current_volume_ml=4000)

    started = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "event_id": "tap-5-closed-1",
            "event_status": "started",
            "tap_id": 5,
            "volume_ml": 10,
            "duration_ms": 1000,
            "card_present": True,
            "valve_open": False,
            "session_state": "card_present_no_session",
            "card_uid": "CARD-555",
            "short_id": None,
            "reason": "flow_detected_when_valve_closed_without_active_session",
        },
    )
    assert started.status_code == 202

    updated = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "event_id": "tap-5-closed-1",
            "event_status": "updated",
            "tap_id": 5,
            "volume_ml": 25,
            "duration_ms": 1800,
            "card_present": True,
            "valve_open": False,
            "session_state": "card_present_no_session",
            "card_uid": "CARD-555",
            "short_id": None,
            "reason": "flow_detected_when_valve_closed_without_active_session",
        },
    )
    assert updated.status_code == 202

    db_session.expire_all()
    refreshed_keg = db_session.query(models.Keg).filter(models.Keg.keg_id == keg.keg_id).one()
    assert refreshed_keg.current_volume_ml == 3975
    assert db_session.query(models.Pour).count() == 0

    non_sale_flow = (
        db_session.query(models.NonSaleFlow)
        .filter(models.NonSaleFlow.event_id == "tap-5-closed-1")
        .one()
    )
    assert non_sale_flow.volume_ml == 25
    assert non_sale_flow.accounted_volume_ml == 25
    assert non_sale_flow.flow_category == "closed_valve_no_session"


def test_flow_summary_separates_sale_non_sale_and_total_volume(client, db_session):
    headers = _login(client)
    tap_1, keg_1 = _create_tap_with_keg(db_session, tap_id=1, current_volume_ml=6000)
    _create_tap_with_keg(db_session, tap_id=2, current_volume_ml=6000)
    _create_sale_pour(db_session, tap_id=tap_1.tap_id, keg_id=keg_1.keg_id, volume_ml=300)

    response = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "event_id": "tap-2-closed-1",
            "event_status": "stopped",
            "tap_id": 2,
            "volume_ml": 40,
            "duration_ms": 1500,
            "card_present": False,
            "valve_open": False,
            "session_state": "no_card_no_session",
            "card_uid": None,
            "short_id": None,
            "reason": "flow_detected_when_valve_closed_without_active_session",
        },
    )
    assert response.status_code == 202

    summary = client.get("/api/reports/flow-summary", headers=headers)
    assert summary.status_code == 200

    payload = summary.json()
    assert payload["sale_volume_ml"] == 300
    assert payload["non_sale_volume_ml"] == 40
    assert payload["total_volume_ml"] == 340
    assert payload["total_volume_ml"] == payload["sale_volume_ml"] + payload["non_sale_volume_ml"]
    assert payload["non_sale_breakdown"] == [{"reason_code": "closed_valve_no_card", "volume_ml": 40}]

    by_tap = {item["tap_id"]: item for item in payload["by_tap"]}
    assert by_tap[1]["sale_volume_ml"] == 300
    assert by_tap[1]["non_sale_volume_ml"] == 0
    assert by_tap[1]["total_volume_ml"] == 300
    assert by_tap[2]["sale_volume_ml"] == 0
    assert by_tap[2]["non_sale_volume_ml"] == 40
    assert by_tap[2]["total_volume_ml"] == 40
