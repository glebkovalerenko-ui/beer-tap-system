def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_guest(client, headers, suffix: str, dob: str = "1990-01-15"):
    response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Guest{suffix}",
            "first_name": "Demo",
            "patronymic": "M2",
            "phone_number": f"+1555000{suffix}",
            "date_of_birth": dob,
            "id_document": f"DOC-{suffix}",
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


def test_visit_invariants_and_card_deactivation(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81001")
    card_uid = "CARD-M2-001"
    _bind_card(client, headers, guest_id, card_uid)

    open_resp = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert open_resp.status_code == 200
    visit_id = open_resp.json()["visit_id"]

    second_for_guest = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert second_for_guest.status_code == 409

    close_resp = client.post(
        f"/api/visits/{visit_id}/close",
        headers=headers,
        json={"closed_reason": "end", "card_returned": False},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
    assert close_resp.json()["card_returned"] is False

    guest_resp = client.get(f"/api/guests/{guest_id}", headers=headers)
    assert guest_resp.status_code == 200
    assert guest_resp.json()["cards"][0]["status"] == "inactive"


def test_second_guest_cannot_open_active_visit_with_busy_card(client):
    headers = _login(client)
    guest_1 = _create_guest(client, headers, suffix="81002")
    guest_2 = _create_guest(client, headers, suffix="81003")

    card_uid = "CARD-M2-002"
    _bind_card(client, headers, guest_1, card_uid)

    open_resp = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_1, "card_uid": card_uid},
    )
    assert open_resp.status_code == 200

    # Re-assign card to another guest is blocked by existing guest binding.
    bind_resp = client.post(
        f"/api/guests/{guest_2}/cards",
        headers=headers,
        json={"card_uid": card_uid},
    )
    assert bind_resp.status_code == 409


def test_topup_allowed_without_active_visit(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81004")

    topup_resp = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 100, "payment_method": "cash"},
    )
    assert topup_resp.status_code == 200
    assert float(topup_resp.json()["balance"]) == 100.0
