import json

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
            "last_name": f"Guest{suffix}",
            "first_name": "M6",
            "patronymic": "LostCard",
            "phone_number": f"+1999000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"M6DOC-{suffix}",
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


def _prepare_active_visit_with_tap(client, suffix: str, card_uid: str):
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
        json={"name": f"M6 Beer {suffix}", "sell_price_per_liter": 500.0},
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
        json={"display_name": f"Tap M6 {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(
        f"/api/taps/{tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_id},
    )
    assert assign_resp.status_code == 200

    return headers, guest_id, visit_id, tap_id, card_uid


def test_report_lost_card_from_active_visit_creates_registry_record(client, db_session):
    headers, guest_id, visit_id, _, card_uid = _prepare_active_visit_with_tap(
        client, suffix="96001", card_uid="CARD-M6-001"
    )

    report = client.post(
        f"/api/visits/{visit_id}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss", "comment": "reported at bar"},
    )
    assert report.status_code == 200
    body = report.json()
    assert body["lost"] is True
    assert body["already_marked"] is False
    assert body["visit"]["visit_id"] == visit_id
    assert body["lost_card"]["visit_id"] == visit_id
    assert body["lost_card"]["guest_id"] == guest_id
    assert body["lost_card"]["card_uid"] == card_uid.lower()

    listed = client.get(f"/api/lost-cards?uid={card_uid}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["card_uid"] == card_uid.lower()

    count = (
        db_session.query(models.LostCard)
        .filter(models.LostCard.card_uid == card_uid.lower())
        .count()
    )
    assert count == 1


def test_authorize_pour_for_lost_card_is_denied_and_audited(client):
    headers, _, visit_id, tap_id, card_uid = _prepare_active_visit_with_tap(
        client, suffix="96002", card_uid="CARD-M6-002"
    )

    report = client.post(
        f"/api/visits/{visit_id}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss"},
    )
    assert report.status_code == 200

    authorize = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": card_uid, "tap_id": tap_id},
    )
    assert authorize.status_code == 403
    assert authorize.json()["detail"]["reason"] == "lost_card"

    audit_resp = client.get("/api/audit/", headers=headers)
    assert audit_resp.status_code == 200
    blocked = [entry for entry in audit_resp.json() if entry["action"] == "lost_card_blocked"]
    assert blocked
    details = json.loads(blocked[0]["details"])
    assert details["card_uid"] == card_uid.lower()
    assert details["tap_id"] == tap_id
    assert "blocked_at" in details


def test_restore_lost_card_requires_visit_resolution_before_reuse(client):
    headers, guest_id, visit_id, tap_id, card_uid = _prepare_active_visit_with_tap(
        client, suffix="96003", card_uid="CARD-M6-003"
    )

    report = client.post(
        f"/api/visits/{visit_id}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss"},
    )
    assert report.status_code == 200

    denied = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": card_uid, "tap_id": tap_id},
    )
    assert denied.status_code == 403

    restore_while_blocked = client.post(f"/api/lost-cards/{card_uid}/restore", headers=headers)
    assert restore_while_blocked.status_code == 409

    replacement_card_uid = "CARD-M6-003-REISSUE"
    reissue = client.post(
        f"/api/visits/{visit_id}/reissue-card",
        headers=headers,
        json={
            "card_uid": replacement_card_uid,
            "reason": "lost_card_reissue",
            "comment": "replacement card issued from pool",
        },
    )
    assert reissue.status_code == 200
    assert reissue.json()["card_uid"] == replacement_card_uid.lower()
    assert reissue.json()["operational_status"] == "active_assigned"

    cards_resp = client.get("/api/cards/", headers=headers)
    assert cards_resp.status_code == 200
    cards_by_uid = {item["card_uid"]: item for item in cards_resp.json()}
    assert cards_by_uid[replacement_card_uid.lower()]["status"] == "assigned_to_visit"
    assert cards_by_uid[card_uid.lower()]["status"] == "lost"

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 20, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    old_card_still_denied = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": card_uid, "tap_id": tap_id},
    )
    assert old_card_still_denied.status_code == 403
    assert old_card_still_denied.json()["detail"]["reason"] == "lost_card"

    authorized = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": replacement_card_uid, "tap_id": tap_id},
    )
    assert authorized.status_code == 200
    assert authorized.json()["allowed"] is True
    assert authorized.json()["visit"]["active_tap_id"] == tap_id

    restore = client.post(f"/api/lost-cards/{card_uid}/restore", headers=headers)
    assert restore.status_code == 200
    assert restore.json()["restored"] is True


def test_restore_lost_card_for_visit_unblocks_same_card_authorize(client):
    headers, guest_id, visit_id, tap_id, card_uid = _prepare_active_visit_with_tap(
        client, suffix="96007", card_uid="CARD-M6-007"
    )

    report = client.post(
        f"/api/visits/{visit_id}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss", "comment": "card was found again"},
    )
    assert report.status_code == 200

    listed = client.get(f"/api/lost-cards?uid={card_uid}", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["requires_visit_recovery"] is True

    restore = client.post(
        f"/api/visits/{visit_id}/restore-lost-card",
        headers=headers,
        json={"reason": "card_recovered", "comment": "cancel lost after verification"},
    )
    assert restore.status_code == 200
    assert restore.json()["operational_status"] == "active_assigned"
    assert restore.json()["card_uid"] == card_uid.lower()

    listed_after = client.get(f"/api/lost-cards?uid={card_uid}", headers=headers)
    assert listed_after.status_code == 200
    assert listed_after.json() == []

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 20, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    authorized = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": card_uid, "tap_id": tap_id},
    )
    assert authorized.status_code == 200
    assert authorized.json()["allowed"] is True
    assert authorized.json()["visit"]["visit_id"] == visit_id


def test_resolve_lost_card_returns_lost_payload(client):
    headers, _, visit_id, _, card_uid = _prepare_active_visit_with_tap(
        client, suffix="96004", card_uid="CARD-M6-004"
    )

    report = client.post(
        f"/api/visits/{visit_id}/report-lost-card",
        headers=headers,
        json={"reason": "guest_reported_loss", "comment": "found near entrance"},
    )
    assert report.status_code == 200

    resolve = client.get(f"/api/cards/{card_uid}/resolve", headers=headers)
    assert resolve.status_code == 200
    body = resolve.json()
    assert body["is_lost"] is True
    assert body["lookup_outcome"] == "active_blocked_lost_card"
    assert body["lost_card"] is not None
    assert body["lost_card"]["visit_id"] == visit_id
    assert body["lost_card"]["comment"] == "found near entrance"
    assert body["active_visit"] is not None
    assert body["active_visit"]["operational_status"] == "active_blocked_lost_card"
    assert body["recommended_action"] == "open_visit_workspace"
    assert set(body["allowed_next_actions"]) == {
        "open_visit_workspace",
        "reissue_card_for_visit",
        "service_close_missing_card",
    }


def test_resolve_card_in_active_visit_returns_active_visit(client):
    headers, guest_id, visit_id, _, card_uid = _prepare_active_visit_with_tap(
        client, suffix="96005", card_uid="CARD-M6-005"
    )

    resolve = client.get(f"/api/cards/{card_uid}/resolve", headers=headers)
    assert resolve.status_code == 200
    body = resolve.json()
    assert body["is_lost"] is False
    assert body["lookup_outcome"] == "active_visit"
    assert body["active_visit"] is not None
    assert body["active_visit"]["visit_id"] == visit_id
    assert body["active_visit"]["guest_id"] == guest_id
    assert body["active_visit"]["operational_status"] == "active_assigned"
    assert body["recommended_action"] == "open_visit_workspace"
    assert set(body["allowed_next_actions"]) == {
        "open_visit_workspace",
        "mark_lost",
        "normal_close_scan",
    }


def test_resolve_available_pool_card_without_active_visit(client):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix="96006")
    card_uid = "CARD-M6-006"
    _bind_card(client, headers, guest_id, card_uid)

    resolve = client.get(f"/api/cards/{card_uid}/resolve", headers=headers)
    assert resolve.status_code == 200
    body = resolve.json()
    assert body["is_lost"] is False
    assert body["lookup_outcome"] == "available_pool_card"
    assert body["active_visit"] is None
    assert body["guest"] is None
    assert body["card"] is not None
    assert body["card"]["status"] == "available"
    assert body["recommended_action"] == "issue_on_open_visit"
    assert body["allowed_next_actions"] == ["issue_on_open_visit"]


def test_resolve_unknown_card_returns_empty_payload(client):
    headers = _login(client)
    resolve = client.get("/api/cards/unknown-card-uid/resolve", headers=headers)
    assert resolve.status_code == 200
    body = resolve.json()
    assert body["card_uid"] == "unknown-card-uid"
    assert body["is_lost"] is False
    assert body["lost_card"] is None
    assert body["active_visit"] is None
    assert body["guest"] is None
    assert body["card"] is None
    assert body["lookup_outcome"] == "unknown_card"
    assert body["recommended_action"] == "issue_on_open_visit"
    assert body["allowed_next_actions"] == ["issue_on_open_visit"]
