from datetime import timezone
import uuid

import models


def _normalize_dt(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_guest(client, headers, suffix: str):
    response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Time{suffix}",
            "first_name": "Guest",
            "patronymic": "M5",
            "phone_number": f"+1777000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"TIME-{suffix}",
        },
    )
    assert response.status_code == 201
    return response.json()["guest_id"]


def test_guest_created_at_is_not_earlier_than_shift_opened_at(client, db_session):
    headers = _login(client)

    open_shift = client.post("/api/shifts/open", headers=headers)
    assert open_shift.status_code == 200
    shift_id = uuid.UUID(open_shift.json()["id"])

    guest_id = uuid.UUID(_create_guest(client, headers, suffix="95001"))

    shift = db_session.query(models.Shift).filter(models.Shift.id == shift_id).one()
    guest = db_session.query(models.Guest).filter(models.Guest.guest_id == guest_id).one()

    assert _normalize_dt(guest.created_at) >= _normalize_dt(shift.opened_at)


def test_new_guests_count_is_stable_for_x_and_z_windows(client):
    headers = _login(client)

    open_shift = client.post("/api/shifts/open", headers=headers)
    assert open_shift.status_code == 200
    shift_id = open_shift.json()["id"]

    _create_guest(client, headers, suffix="95011")

    x_report = client.get(f"/api/shifts/{shift_id}/reports/x", headers=headers)
    assert x_report.status_code == 200
    assert x_report.json()["totals"]["new_guests_count"] == 1

    close_shift = client.post("/api/shifts/close", headers=headers)
    assert close_shift.status_code == 200

    # Guest created after close must not enter Z window for this shift.
    _create_guest(client, headers, suffix="95012")

    z_report_first = client.post(f"/api/shifts/{shift_id}/reports/z", headers=headers)
    assert z_report_first.status_code == 200
    assert z_report_first.json()["payload"]["totals"]["new_guests_count"] == 1

    z_report_second = client.post(f"/api/shifts/{shift_id}/reports/z", headers=headers)
    assert z_report_second.status_code == 200
    assert z_report_second.json()["payload"]["totals"]["new_guests_count"] == 1
