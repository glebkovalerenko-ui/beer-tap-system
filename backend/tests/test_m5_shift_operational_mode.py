import uuid

import models
from sqlalchemy import func


def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_guest(client, headers, suffix: str):
    response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Shift{suffix}",
            "first_name": "Guest",
            "patronymic": "M5",
            "phone_number": f"+1888000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"M5DOC-{suffix}",
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


def _create_tap_with_keg(client, headers, suffix: str):
    beverage_resp = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": f"M5 Beer {suffix}", "sell_price_per_liter": 500.0},
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
        json={"display_name": f"Tap M5 {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(
        f"/api/taps/{tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_id},
    )
    assert assign_resp.status_code == 200
    return tap_id


def test_cannot_open_visit_without_open_shift(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="93001")

    open_visit = client.post("/api/visits/open", headers=headers, json={"guest_id": guest_id})
    assert open_visit.status_code == 403
    assert open_visit.json()["detail"] == "Shift is closed"


def test_cannot_authorize_without_open_shift(client):
    headers = _login(client)

    auth_resp = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M5-93002", "tap_id": 1},
    )
    assert auth_resp.status_code == 403
    assert auth_resp.json()["detail"] == "Shift is closed"


def test_cannot_close_shift_with_active_visit(client):
    headers = _login(client)
    open_shift = client.post("/api/shifts/open", headers=headers)
    assert open_shift.status_code == 200

    guest_id = _create_guest(client, headers, suffix="93003")
    visit_resp = client.post("/api/visits/open", headers=headers, json={"guest_id": guest_id})
    assert visit_resp.status_code == 200

    close_shift = client.post("/api/shifts/close", headers=headers)
    assert close_shift.status_code == 409
    assert close_shift.json()["detail"] == "active_visits_exist"


def test_cannot_close_shift_with_pending_sync(client, db_session):
    headers = _login(client)
    open_shift = client.post("/api/shifts/open", headers=headers)
    assert open_shift.status_code == 200

    guest_id = _create_guest(client, headers, suffix="93004")
    card_uid = "CARD-M5-93004"
    _bind_card(client, headers, guest_id, card_uid)
    visit_resp = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert visit_resp.status_code == 200
    visit_id = visit_resp.json()["visit_id"]

    tap_id = _create_tap_with_keg(client, headers, suffix="93004")

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 300, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": card_uid, "tap_id": tap_id},
    )
    assert authorize.status_code == 200

    close_visit = client.post(
        f"/api/visits/{visit_id}/close",
        headers=headers,
        json={"closed_reason": "checkout", "card_returned": True},
    )
    assert close_visit.status_code == 409
    assert close_visit.json()["detail"] == "pending_sync_exists_for_visit"

    # Simulate legacy/abnormal state where a visit is already closed but pending_sync remains.
    db_session.query(models.Visit).filter(models.Visit.visit_id == uuid.UUID(visit_id)).update(
        {
            models.Visit.status: "closed",
            models.Visit.closed_reason: "forced_test_close",
            models.Visit.closed_at: func.now(),
            models.Visit.active_tap_id: None,
            models.Visit.lock_set_at: None,
        }
    )
    db_session.commit()

    close_shift = client.post("/api/shifts/close", headers=headers)
    assert close_shift.status_code == 409
    assert close_shift.json()["detail"] == "pending_sync_pours_exist"


def test_shift_open_close_happy_path(client):
    headers = _login(client)

    current_before = client.get("/api/shifts/current", headers=headers)
    assert current_before.status_code == 200
    assert current_before.json()["status"] == "closed"
    assert current_before.json()["shift"] is None

    opened = client.post("/api/shifts/open", headers=headers)
    assert opened.status_code == 200
    assert opened.json()["status"] == "open"
    assert opened.json()["closed_at"] is None
    shift_id = opened.json()["id"]

    current_open = client.get("/api/shifts/current", headers=headers)
    assert current_open.status_code == 200
    assert current_open.json()["status"] == "open"
    assert current_open.json()["shift"]["id"] == shift_id

    closed = client.post("/api/shifts/close", headers=headers)
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert closed.json()["closed_at"] is not None

    current_after = client.get("/api/shifts/current", headers=headers)
    assert current_after.status_code == 200
    assert current_after.json()["status"] == "closed"
    assert current_after.json()["shift"] is None
