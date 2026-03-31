def _login(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    shift_open = client.post("/api/shifts/open", headers=headers)
    assert shift_open.status_code in (200, 409)
    return headers


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


def _register_card(client, headers, card_uid: str) -> str:
    response = client.post("/api/cards/", headers=headers, json={"card_uid": card_uid})
    assert response.status_code == 201
    return response.json()["card_uid"]


def _open_visit(client, headers, guest_id: str, card_uid: str):
    response = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert response.status_code == 200
    return response.json()


def test_open_visit_requires_registered_pool_card_and_normal_close_returns_it(client):
    headers = _login(client)
    guest_1 = _create_guest(client, headers, suffix="81001")
    guest_2 = _create_guest(client, headers, suffix="81002")
    card_uid = _register_card(client, headers, "CARD-M2-001")

    opened = _open_visit(client, headers, guest_1, card_uid)
    assert opened["card_uid"] == "card-m2-001"
    assert opened["operational_status"] == "active_assigned"

    close_resp = client.post(
        f"/api/visits/{opened['visit_id']}/close",
        headers=headers,
        json={"closed_reason": "guest_checkout", "returned_card_uid": "CARD-M2-001"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
    assert close_resp.json()["operational_status"] == "closed_ok"
    assert close_resp.json()["card_returned"] is True
    assert close_resp.json()["return_method"] == "operator_nfc"

    card_resp = client.get("/api/cards/", headers=headers)
    assert card_resp.status_code == 200
    card = next(item for item in card_resp.json() if item["card_uid"] == "card-m2-001")
    assert card["status"] == "returned_to_pool"

    reopened = _open_visit(client, headers, guest_2, "CARD-M2-001")
    assert reopened["card_uid"] == "card-m2-001"
    assert reopened["operational_status"] == "active_assigned"


def test_second_guest_cannot_open_active_visit_with_busy_card(client):
    headers = _login(client)
    guest_1 = _create_guest(client, headers, suffix="81003")
    guest_2 = _create_guest(client, headers, suffix="81004")
    card_uid = _register_card(client, headers, "CARD-M2-002")

    open_resp = _open_visit(client, headers, guest_1, card_uid)
    assert open_resp["operational_status"] == "active_assigned"

    second_open = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_2, "card_uid": card_uid},
    )
    assert second_open.status_code == 409


def test_topup_allowed_without_active_visit(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81005")

    topup_resp = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 100, "payment_method": "cash"},
    )
    assert topup_resp.status_code == 200
    assert float(topup_resp.json()["balance"]) == 100.0


def test_open_visit_without_card_is_rejected(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81006")

    open_resp = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id},
    )
    assert open_resp.status_code == 422


def test_open_visit_conflict_includes_existing_visit_id(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81007")
    card_uid = _register_card(client, headers, "CARD-M2-003")

    first_open = _open_visit(client, headers, guest_id, card_uid)

    second_open = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert second_open.status_code == 409
    assert second_open.json()["detail"]["message"] == "Guest already has an active visit"
    assert second_open.json()["detail"]["visit_id"] == first_open["visit_id"]


def test_active_visits_list_includes_operational_status_and_card_uid(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81008")
    card_uid = _register_card(client, headers, "CARD-M2-004")

    _open_visit(client, headers, guest_id, card_uid)

    list_resp = client.get("/api/visits/active", headers=headers)
    assert list_resp.status_code == 200
    visit_item = next(v for v in list_resp.json() if v["guest_id"] == guest_id)
    assert visit_item["card_uid"] == "card-m2-004"
    assert visit_item["operational_status"] == "active_assigned"


def test_assign_card_endpoint_is_not_available_for_normal_operator_flow(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81009")
    card_uid = _register_card(client, headers, "CARD-M2-005")
    visit = _open_visit(client, headers, guest_id, card_uid)

    assign_resp = client.post(
        f"/api/visits/{visit['visit_id']}/assign-card",
        headers=headers,
        json={"card_uid": "card-m2-other"},
    )
    assert assign_resp.status_code == 409


def test_lost_card_blocks_normal_close_until_reissue_or_service_close(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81010")
    old_card_uid = _register_card(client, headers, "CARD-M2-006")
    new_card_uid = _register_card(client, headers, "CARD-M2-007")
    visit = _open_visit(client, headers, guest_id, old_card_uid)

    lost_resp = client.post(
        f"/api/visits/{visit['visit_id']}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss", "comment": "Lost on the way out"},
    )
    assert lost_resp.status_code == 200
    assert lost_resp.json()["visit"]["operational_status"] == "active_blocked_lost_card"

    close_resp = client.post(
        f"/api/visits/{visit['visit_id']}/close",
        headers=headers,
        json={"closed_reason": "guest_checkout", "returned_card_uid": old_card_uid},
    )
    assert close_resp.status_code == 409

    reissue_resp = client.post(
        f"/api/visits/{visit['visit_id']}/reissue-card",
        headers=headers,
        json={"card_uid": new_card_uid, "reason": "lost_card_reissue", "comment": "Replacement issued"},
    )
    assert reissue_resp.status_code == 200
    assert reissue_resp.json()["card_uid"] == "card-m2-007"
    assert reissue_resp.json()["operational_status"] == "active_assigned"


def test_blocked_lost_reissue_auto_registers_unknown_replacement_card(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81012")
    old_card_uid = _register_card(client, headers, "CARD-M2-010")
    visit = _open_visit(client, headers, guest_id, old_card_uid)

    lost_resp = client.post(
        f"/api/visits/{visit['visit_id']}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss", "comment": "Lost on the way out"},
    )
    assert lost_resp.status_code == 200

    reissue_resp = client.post(
        f"/api/visits/{visit['visit_id']}/reissue-card",
        headers=headers,
        json={"card_uid": "CARD-M2-010-NEW", "reason": "lost_card_reissue", "comment": "Replacement issued immediately"},
    )
    assert reissue_resp.status_code == 200
    assert reissue_resp.json()["card_uid"] == "card-m2-010-new"
    assert reissue_resp.json()["operational_status"] == "active_assigned"

    cards_resp = client.get("/api/cards/", headers=headers)
    assert cards_resp.status_code == 200
    cards_by_uid = {item["card_uid"]: item for item in cards_resp.json()}
    assert cards_by_uid["card-m2-010-new"]["status"] == "assigned_to_visit"
    assert cards_by_uid["card-m2-010"]["status"] == "lost"


def test_blocked_lost_reissue_rejects_lost_or_busy_replacement_card(client):
    headers = _login(client)
    guest_a = _create_guest(client, headers, suffix="81013")
    guest_b = _create_guest(client, headers, suffix="81014")
    lost_card_uid = _register_card(client, headers, "CARD-M2-011")
    busy_card_uid = _register_card(client, headers, "CARD-M2-012")

    visit_a = _open_visit(client, headers, guest_a, lost_card_uid)
    _open_visit(client, headers, guest_b, busy_card_uid)

    lost_resp = client.post(
        f"/api/visits/{visit_a['visit_id']}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss"},
    )
    assert lost_resp.status_code == 200

    lost_reuse_resp = client.post(
        f"/api/visits/{visit_a['visit_id']}/reissue-card",
        headers=headers,
        json={"card_uid": lost_card_uid, "reason": "lost_card_reissue", "comment": None},
    )
    assert lost_reuse_resp.status_code == 409
    assert "lost" in lost_reuse_resp.json()["detail"]

    busy_reuse_resp = client.post(
        f"/api/visits/{visit_a['visit_id']}/reissue-card",
        headers=headers,
        json={"card_uid": busy_card_uid, "reason": "lost_card_reissue", "comment": None},
    )
    assert busy_reuse_resp.status_code == 409
    assert busy_reuse_resp.json()["detail"] == "Card already used by another active visit"


def test_service_close_missing_card_keeps_visit_closed_missing_and_card_lost(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="81011")
    card_uid = _register_card(client, headers, "CARD-M2-008")
    visit = _open_visit(client, headers, guest_id, card_uid)

    service_close_resp = client.post(
        f"/api/visits/{visit['visit_id']}/service-close",
        headers=headers,
        json={
            "closed_reason": "service_close_missing_card",
            "reason_code": "card_missing",
            "comment": "Guest left without returning card",
        },
    )
    assert service_close_resp.status_code == 200
    assert service_close_resp.json()["status"] == "closed"
    assert service_close_resp.json()["operational_status"] == "closed_missing_card"
    assert service_close_resp.json()["card_returned"] is False

    resolve_resp = client.get(f"/api/cards/{card_uid}/resolve", headers=headers)
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["lookup_outcome"] == "lost_card"


def test_card_registration_normalizes_uid_and_blocks_case_only_duplicates(client):
    headers = _login(client)
    created = client.post("/api/cards/", headers=headers, json={"card_uid": "CARD-M2-009"})
    assert created.status_code == 201
    assert created.json()["card_uid"] == "card-m2-009"

    duplicate = client.post("/api/cards/", headers=headers, json={"card_uid": "card-m2-009"})
    assert duplicate.status_code == 409
