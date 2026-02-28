import json
import uuid

import models


def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    shift_open = client.post("/api/shifts/open", headers=headers)
    assert shift_open.status_code in (200, 409)
    return headers


def _create_guest(client, headers, suffix: str):
    response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Clamp{suffix}",
            "first_name": "Guest",
            "patronymic": "M6",
            "phone_number": f"+1777100{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"M6CLAMP-{suffix}",
        },
    )
    assert response.status_code == 201
    return response.json()["guest_id"]


def _bind_card(client, headers, guest_id: str, card_uid: str):
    response = client.post(
        f"/api/guests/{guest_id}/cards",
        headers=headers,
        json={"card_uid": card_uid},
    )
    assert response.status_code == 200


def _prepare_active_visit(client, suffix: str, card_uid: str, *, sell_price_per_liter, topup_amount):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix=suffix)
    _bind_card(client, headers, guest_id, card_uid)

    visit_resp = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert visit_resp.status_code == 200
    visit_id = visit_resp.json()["visit_id"]

    beverage_resp = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": f"M6 Clamp Beer {suffix}", "sell_price_per_liter": sell_price_per_liter},
    )
    assert beverage_resp.status_code == 201
    beverage_id = beverage_resp.json()["beverage_id"]

    keg_resp = client.post(
        "/api/kegs/",
        headers=headers,
        json={
            "beverage_id": beverage_id,
            "initial_volume_ml": 30000,
            "purchase_price": 1000.0,
        },
    )
    assert keg_resp.status_code == 201
    keg_id = keg_resp.json()["keg_id"]

    tap_resp = client.post(
        "/api/taps/",
        headers=headers,
        json={"display_name": f"Tap M6 Clamp {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(
        f"/api/taps/{tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_id},
    )
    assert assign_resp.status_code == 200

    if topup_amount:
        topup = client.post(
            f"/api/guests/{guest_id}/topup",
            headers=headers,
            json={"amount": topup_amount, "payment_method": "cash"},
        )
        assert topup.status_code == 200

    return headers, guest_id, visit_id, tap_id


def test_authorize_denies_when_balance_below_min_start_threshold(client, db_session):
    headers, guest_id, visit_id, tap_id = _prepare_active_visit(
        client,
        suffix="97001",
        card_uid="CARD-M6-97001",
        sell_price_per_liter=500.0,
        topup_amount=9.0,
    )

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M6-97001", "tap_id": tap_id},
    )
    assert authorize.status_code == 403
    detail = authorize.json()["detail"]
    assert detail["reason"] == "insufficient_funds"
    assert detail["context"]["min_start_ml"] == 20
    assert detail["context"]["price_per_ml_cents"] == 50
    assert detail["context"]["balance_cents"] == 900
    assert detail["context"]["max_volume_ml"] == 16
    assert detail["context"]["required_cents"] == 1000

    db_session.expire_all()
    pending_count = (
        db_session.query(models.Pour)
        .filter(models.Pour.visit_id == uuid.UUID(visit_id), models.Pour.tap_id == tap_id)
        .count()
    )
    assert pending_count == 0

    visit = client.get("/api/visits/active/by-card/CARD-M6-97001", headers=headers)
    assert visit.status_code == 200
    assert visit.json()["active_tap_id"] is None

    guest = client.get(f"/api/guests/{guest_id}", headers=headers)
    assert guest.status_code == 200
    assert guest.json()["balance"] == "9.00"


def test_authorize_returns_max_volume_with_floor_and_safety_applied(client):
    headers, _, _, tap_id = _prepare_active_visit(
        client,
        suffix="97002",
        card_uid="CARD-M6-97002",
        sell_price_per_liter=123.0,
        topup_amount=10.0,
    )

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M6-97002", "tap_id": tap_id},
    )
    assert authorize.status_code == 200
    body = authorize.json()
    assert body["allowed"] is True
    assert body["min_start_ml"] == 20
    assert body["price_per_ml_cents"] == 13
    assert body["balance_cents"] == 1000
    assert body["allowed_overdraft_cents"] == 0
    assert body["safety_ml"] == 2
    assert body["max_volume_ml"] == 74
    assert body["lock_set_at"] is not None


def test_pending_sync_created_only_when_authorize_allowed(client, db_session):
    headers, guest_id, visit_id, tap_id = _prepare_active_visit(
        client,
        suffix="97003",
        card_uid="CARD-M6-97003",
        sell_price_per_liter=500.0,
        topup_amount=9.0,
    )

    denied = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M6-97003", "tap_id": tap_id},
    )
    assert denied.status_code == 403

    pending_after_deny = (
        db_session.query(models.Pour)
        .filter(models.Pour.visit_id == uuid.UUID(visit_id), models.Pour.tap_id == tap_id)
        .count()
    )
    assert pending_after_deny == 0

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 5.0, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    allowed = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M6-97003", "tap_id": tap_id},
    )
    assert allowed.status_code == 200

    db_session.expire_all()
    pending = (
        db_session.query(models.Pour)
        .filter(
            models.Pour.visit_id == uuid.UUID(visit_id),
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
        )
        .one()
    )
    assert pending.authorized_at is not None


def test_authorize_sync_updates_same_pour_and_clears_lock(client, db_session):
    headers, guest_id, visit_id, tap_id = _prepare_active_visit(
        client,
        suffix="97004",
        card_uid="CARD-M6-97004",
        sell_price_per_liter=500.0,
        topup_amount=20.0,
    )

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M6-97004", "tap_id": tap_id},
    )
    assert authorize.status_code == 200
    assert authorize.json()["max_volume_ml"] == 38

    pending = (
        db_session.query(models.Pour)
        .filter(
            models.Pour.visit_id == uuid.UUID(visit_id),
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
        )
        .one()
    )
    pending_pour_id = pending.pour_id

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m6-clamp-sync-97004",
                    "card_uid": "CARD-M6-97004",
                    "tap_id": tap_id,
                    "short_id": "L97004",
                    "duration_ms": 3000,
                    "volume_ml": 30,
                    "price_cents": 1500,
                }
            ]
        },
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["results"][0]["status"] == "accepted"

    db_session.expire_all()
    synced = db_session.query(models.Pour).filter(models.Pour.pour_id == pending_pour_id).one()
    assert synced.sync_status == "synced"
    assert synced.client_tx_id == "m6-clamp-sync-97004"
    assert synced.short_id == "L97004"
    assert synced.volume_ml == 30
    assert synced.synced_at is not None

    visit = client.get("/api/visits/active/by-card/CARD-M6-97004", headers=headers)
    assert visit.status_code == 200
    assert visit.json()["active_tap_id"] is None

    guest = client.get(f"/api/guests/{guest_id}", headers=headers)
    assert guest.status_code == 200
    assert guest.json()["balance"] == "5.00"


def test_insufficient_funds_deny_writes_audit_event(client):
    headers, _, visit_id, tap_id = _prepare_active_visit(
        client,
        suffix="97005",
        card_uid="CARD-M6-97005",
        sell_price_per_liter=500.0,
        topup_amount=9.0,
    )

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M6-97005", "tap_id": tap_id},
    )
    assert authorize.status_code == 403

    audit_resp = client.get("/api/audit/", headers=headers)
    assert audit_resp.status_code == 200
    blocked = [entry for entry in audit_resp.json() if entry["action"] == "insufficient_funds_blocked"]
    assert blocked
    details = json.loads(blocked[0]["details"])
    assert details["visit_id"] == visit_id
    assert details["tap_id"] == tap_id
    assert details["balance_cents"] == 900
    assert details["required_cents"] == 1000
    assert details["min_start_ml"] == 20
