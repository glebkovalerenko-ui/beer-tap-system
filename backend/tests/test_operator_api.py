from datetime import date, datetime, timezone
from decimal import Decimal

import models
from operator_stream import operator_stream_hub


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


def _seed_closed_timeout_visit(db_session):
    now = datetime.now(timezone.utc)
    guest = models.Guest(
        last_name="Petrova",
        first_name="Anna",
        patronymic="Sergeevna",
        phone_number="+79990002233",
        date_of_birth=date(1992, 2, 2),
        id_document="4510 654321",
        balance=Decimal("350.00"),
        is_active=True,
    )
    card = models.Card(
        card_uid="04AB7815CD6B81",
        guest=guest,
        status="inactive",
    )
    visit = models.Visit(
        guest=guest,
        card=card,
        card_uid=card.card_uid,
        status="closed",
        opened_at=now,
        closed_at=now,
        closed_reason="timeout_close",
        active_tap_id=None,
        lock_set_at=None,
        card_returned=True,
    )
    db_session.add_all([guest, card, visit])
    db_session.commit()
    return visit


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


def test_operator_sessions_return_projection_filters_and_detail(client, db_session):
    _seed_operator_fixture(db_session)
    closed_visit = _seed_closed_timeout_visit(db_session)
    headers = _auth_headers(client, "shift_lead")

    active_only = client.get(
        "/api/operator/sessions",
        params={"active_only": "true"},
        headers=headers,
    )
    assert active_only.status_code == 200
    active_payload = active_only.json()
    assert active_payload["header"]["active_sessions"] == 1
    assert len(active_payload["pinned_active_sessions"]) == 1
    assert len(active_payload["items"]) == 1
    assert active_payload["items"][0]["visit_id"] == active_payload["pinned_active_sessions"][0]["visit_id"]

    filtered = client.get(
        "/api/operator/sessions",
        params={
            "period_preset": "today",
            "completion_source": "timeout",
            "zero_volume_abort_only": "true",
        },
        headers=headers,
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["header"]["zero_volume_abort_sessions"] == 1
    assert len(filtered_payload["items"]) == 1
    timeout_item = filtered_payload["items"][0]
    assert timeout_item["visit_id"] == str(closed_visit.visit_id)
    assert timeout_item["completion_source"] == "timeout"
    assert timeout_item["has_zero_volume_abort"] is True

    detail_response = client.get(
        f"/api/operator/sessions/{active_payload['pinned_active_sessions'][0]['visit_id']}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["summary"]["visit_status"] == "active"
    assert detail_payload["summary"]["has_unsynced"] is True
    assert detail_payload["display_context"]["available"] is True
    assert detail_payload["safe_actions"]["close"]["allowed"] is True
    assert detail_payload["safe_actions"]["close"]["confirm_required"] is True
    assert detail_payload["safe_actions"]["force_unlock"]["allowed"] is True
    assert detail_payload["safe_actions"]["mark_lost_card"]["allowed"] is True
    assert any(item["kind"] == "open" for item in detail_payload["narrative"])
    assert any(item["kind"] == "sync_result" for item in detail_payload["narrative"])


def test_operator_system_health_returns_mode_queue_and_blocked_actions(client, db_session):
    _seed_operator_fixture(db_session)
    headers = _auth_headers(client, "shift_lead")

    response = client.get("/api/operator/system", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["mode"] == "controller_only"
    assert payload["queue_summary"]["pending_items"] == 1
    assert payload["queue_summary"]["unsynced_sessions"] == 1
    assert payload["stale_summary"]["stale_device_count"] >= 2
    assert payload["blocked_actions"]["tap_control"]["allowed"] is False
    assert payload["blocked_actions"]["session_mutation"]["allowed"] is False
    assert payload["blocked_actions"]["incident_mutation"]["allowed"] is False
    assert payload["blocked_actions"]["emergency_stop"]["allowed"] is True
    assert payload["actionable_next_steps"]


def test_operator_stream_ticket_and_websocket_emit_invalidations(client, db_session):
    _seed_operator_fixture(db_session)
    headers = _auth_headers(client, "shift_lead")

    ticket_response = client.post("/api/operator/stream-ticket", headers=headers)
    assert ticket_response.status_code == 200
    ticket_payload = ticket_response.json()
    assert ticket_payload["ticket"]
    assert ticket_payload["heartbeat_interval_ms"] == 5000
    assert ticket_payload["websocket_path"] == "/api/operator/stream"

    with client.websocket_connect(f"/api/operator/stream?ticket={ticket_payload['ticket']}") as websocket:
        hello = websocket.receive_json()
        assert hello["event_type"] == "hello"
        assert hello["resource"] == "system"

        operator_stream_hub.emit_invalidation(
            resource="session",
            entity_id="visit-123",
            severity="warning",
            reason="test_invalidation",
        )
        invalidation = websocket.receive_json()
        assert invalidation["event_type"] == "session.updated"
        assert invalidation["entity_id"] == "visit-123"
        assert invalidation["severity"] == "warning"
        assert invalidation["reason"] == "test_invalidation"
