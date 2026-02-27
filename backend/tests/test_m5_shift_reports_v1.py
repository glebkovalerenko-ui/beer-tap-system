from datetime import date, timedelta
import uuid

import models


def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _open_shift(client, headers):
    response = client.post("/api/shifts/open", headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


def _create_guest(client, headers, suffix: str):
    response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Report{suffix}",
            "first_name": "Guest",
            "patronymic": "M5",
            "phone_number": f"+1999000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"RPT-{suffix}",
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
        json={"name": f"Report Beer {suffix}", "sell_price_per_liter": 500.0},
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
        json={"display_name": f"Tap Reports {suffix}"},
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


def _create_synced_pour_for_open_shift(client, headers, suffix: str):
    guest_id = _create_guest(client, headers, suffix=suffix)
    card_uid = f"CARD-RPT-{suffix}"
    _bind_card(client, headers, guest_id=guest_id, card_uid=card_uid)
    tap_id = _create_tap_with_keg(client, headers, suffix=suffix)

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 300, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    open_visit = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert open_visit.status_code == 200
    visit_id = open_visit.json()["visit_id"]

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": card_uid, "tap_id": tap_id},
    )
    assert authorize.status_code == 200

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": f"m5-report-sync-{suffix}",
                    "card_uid": card_uid,
                    "tap_id": tap_id,
                    "short_id": f"S{suffix[-5:]}",
                    "duration_ms": 5000,
                    "volume_ml": 200,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["results"][0]["status"] == "accepted"
    return visit_id


def test_x_report_computes_and_returns_payload(client):
    headers = _login(client)
    shift_id = _open_shift(client, headers)
    _create_synced_pour_for_open_shift(client, headers, suffix="94001")

    x_report = client.get(f"/api/shifts/{shift_id}/reports/x", headers=headers)
    assert x_report.status_code == 200
    payload = x_report.json()

    assert payload["meta"]["shift_id"] == shift_id
    assert payload["meta"]["report_type"] == "X"
    assert payload["totals"]["pours_count"] == 1
    assert payload["totals"]["total_volume_ml"] == 200
    assert payload["totals"]["total_amount_cents"] == 10000
    assert payload["totals"]["new_guests_count"] == 1
    assert payload["totals"]["pending_sync_count"] == 0
    assert payload["totals"]["reconciled_count"] == 0
    assert payload["totals"]["mismatch_count"] == 0
    assert payload["kegs"]["status"] == "not_available_yet"
    assert len(payload["by_tap"]) == 1


def test_z_report_requires_closed_shift(client):
    headers = _login(client)
    shift_id = _open_shift(client, headers)

    z_report = client.post(f"/api/shifts/{shift_id}/reports/z", headers=headers)
    assert z_report.status_code == 409
    assert z_report.json()["detail"] == "Shift must be closed for Z report"


def test_z_report_is_idempotent(client):
    headers = _login(client)
    shift_id = _open_shift(client, headers)

    close_shift = client.post("/api/shifts/close", headers=headers)
    assert close_shift.status_code == 200

    first = client.post(f"/api/shifts/{shift_id}/reports/z", headers=headers)
    assert first.status_code == 200
    first_json = first.json()

    second = client.post(f"/api/shifts/{shift_id}/reports/z", headers=headers)
    assert second.status_code == 200
    second_json = second.json()

    assert first_json["report_id"] == second_json["report_id"]
    assert first_json["payload"] == second_json["payload"]
    assert first_json["report_type"] == "Z"


def test_z_report_counts_only_guests_created_inside_shift_window(client, db_session):
    headers = _login(client)
    shift_id = _open_shift(client, headers)

    guest_outside_before = _create_guest(client, headers, suffix="94110")
    guest_inside_1 = _create_guest(client, headers, suffix="94111")
    guest_inside_2 = _create_guest(client, headers, suffix="94112")

    close_shift = client.post("/api/shifts/close", headers=headers)
    assert close_shift.status_code == 200

    shift_uuid = uuid.UUID(shift_id)
    shift = db_session.query(models.Shift).filter(models.Shift.id == shift_uuid).one()
    midpoint = shift.opened_at + ((shift.closed_at - shift.opened_at) / 2)

    guest_outside_after = _create_guest(client, headers, suffix="94113")

    db_session.query(models.Guest).filter(models.Guest.guest_id == uuid.UUID(guest_outside_before)).update(
        {"created_at": shift.opened_at - timedelta(seconds=10)}
    )
    db_session.query(models.Guest).filter(models.Guest.guest_id == uuid.UUID(guest_inside_1)).update(
        {"created_at": midpoint}
    )
    db_session.query(models.Guest).filter(models.Guest.guest_id == uuid.UUID(guest_inside_2)).update(
        {"created_at": midpoint}
    )
    db_session.query(models.Guest).filter(models.Guest.guest_id == uuid.UUID(guest_outside_after)).update(
        {"created_at": shift.closed_at + timedelta(seconds=10)}
    )
    db_session.commit()

    z_report = client.post(f"/api/shifts/{shift_id}/reports/z", headers=headers)
    assert z_report.status_code == 200
    payload = z_report.json()["payload"]
    assert payload["totals"]["new_guests_count"] == 2


def test_z_report_date_range_listing(client):
    headers = _login(client)

    shift_1 = _open_shift(client, headers)
    close_1 = client.post("/api/shifts/close", headers=headers)
    assert close_1.status_code == 200
    z_1 = client.post(f"/api/shifts/{shift_1}/reports/z", headers=headers)
    assert z_1.status_code == 200

    shift_2 = _open_shift(client, headers)
    close_2 = client.post("/api/shifts/close", headers=headers)
    assert close_2.status_code == 200
    z_2 = client.post(f"/api/shifts/{shift_2}/reports/z", headers=headers)
    assert z_2.status_code == 200

    today = date.today().isoformat()
    listed = client.get(f"/api/shifts/reports/z?from={today}&to={today}", headers=headers)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 2

    shift_ids = {item["shift_id"] for item in items}
    assert shift_1 in shift_ids
    assert shift_2 in shift_ids
    for item in items:
        assert "report_id" in item
        assert "generated_at" in item
        assert "total_volume_ml" in item
        assert "total_amount_cents" in item
