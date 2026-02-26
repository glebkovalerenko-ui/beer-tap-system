import json


def _login(client):
    response = client.post(
        "/api/token", data={"username": "admin", "password": "fake_password"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    shift_open = client.post("/api/shifts/open", headers=headers)
    assert shift_open.status_code in (200, 409)
    return headers


def _create_guest(client, headers, suffix: str):
    response = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"Guest{suffix}",
            "first_name": "M3",
            "patronymic": "Lock",
            "phone_number": f"+1666000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"M3DOC-{suffix}",
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


def _open_visit(client, headers, guest_id: str, card_uid: str):
    response = client.post(
        "/api/visits/open",
        headers=headers,
        json={"guest_id": guest_id, "card_uid": card_uid},
    )
    assert response.status_code == 200
    return response.json()["visit_id"]


def _prepare_active_visit(client, suffix: str, card_uid: str):
    headers = _login(client)
    guest_id = _create_guest(client, headers, suffix=suffix)
    _bind_card(client, headers, guest_id, card_uid)
    visit_id = _open_visit(client, headers, guest_id, card_uid)

    beverage_resp = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": f"M3 Beer {suffix}", "sell_price_per_liter": 500.0},
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
        json={"display_name": f"Tap M3 {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(
        f"/api/taps/{tap_id}/keg", headers=headers, json={"keg_id": keg_id}
    )
    assert assign_resp.status_code == 200

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 500, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    return headers, guest_id, visit_id, tap_id


def test_authorize_sets_lock_and_second_tap_gets_409(client):
    headers, _, _, tap_id = _prepare_active_visit(
        client, suffix="91001", card_uid="CARD-M3-001"
    )

    auth_1 = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M3-001", "tap_id": tap_id},
    )
    assert auth_1.status_code == 200
    assert auth_1.json()["visit"]["active_tap_id"] == tap_id

    extra_tap = client.post(
        "/api/taps/", headers=headers, json={"display_name": "Tap M3 conflict"}
    )
    assert extra_tap.status_code == 201
    conflict_tap_id = extra_tap.json()["tap_id"]

    auth_2 = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M3-001", "tap_id": conflict_tap_id},
    )
    assert auth_2.status_code == 409
    assert f"Tap {tap_id}" in auth_2.json()["detail"]


def test_sync_releases_lock_and_next_authorize_on_other_tap_succeeds(client):
    headers, _, _, tap_id = _prepare_active_visit(
        client, suffix="91002", card_uid="CARD-M3-002"
    )

    auth_resp = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M3-002", "tap_id": tap_id},
    )
    assert auth_resp.status_code == 200

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m3-sync-001",
                    "card_uid": "CARD-M3-002",
                    "tap_id": tap_id,
                    "short_id": "M30001",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 200,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["results"][0]["status"] == "accepted"

    visit_resp = client.get("/api/visits/active/by-card/CARD-M3-002", headers=headers)
    assert visit_resp.status_code == 200
    assert visit_resp.json()["active_tap_id"] is None


def test_force_unlock_clears_lock_and_audits(client):
    headers, _, visit_id, tap_id = _prepare_active_visit(
        client, suffix="91003", card_uid="CARD-M3-003"
    )

    auth_resp = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M3-003", "tap_id": tap_id},
    )
    assert auth_resp.status_code == 200

    unlock_resp = client.post(
        f"/api/visits/{visit_id}/force-unlock",
        headers=headers,
        json={"reason": "network_stuck", "comment": "operator recovery"},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["active_tap_id"] is None

    audit_resp = client.get("/api/audit/", headers=headers)
    assert audit_resp.status_code == 200
    assert any(log["action"] == "visit_force_unlock" for log in audit_resp.json())


def test_sync_with_other_tap_returns_409_and_late_sync_is_rejected(client):
    headers, _, visit_id, tap_id = _prepare_active_visit(
        client, suffix="91004", card_uid="CARD-M3-004"
    )

    auth_resp = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M3-004", "tap_id": tap_id},
    )
    assert auth_resp.status_code == 200

    beverage_resp = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": "M3 Beer conflict 91004", "sell_price_per_liter": 500.0},
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

    tap_resp = client.post(
        "/api/taps/",
        headers=headers,
        json={"display_name": "Tap M3 sync conflict"},
    )
    assert tap_resp.status_code == 201
    conflict_tap_id = tap_resp.json()["tap_id"]
    assign_resp = client.put(
        f"/api/taps/{conflict_tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_resp.json()["keg_id"]},
    )
    assert assign_resp.status_code == 200

    bad_sync = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m3-sync-002",
                    "card_uid": "CARD-M3-004",
                    "tap_id": conflict_tap_id,
                    "short_id": "M30002",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 200,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert bad_sync.status_code == 409

    unlock_resp = client.post(
        f"/api/visits/{visit_id}/force-unlock",
        headers=headers,
        json={"reason": "manual_intervention", "comment": "late sync expected"},
    )
    assert unlock_resp.status_code == 200

    late_sync = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m3-sync-003",
                    "card_uid": "CARD-M3-004",
                    "tap_id": tap_id,
                    "short_id": "M30003",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 200,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert late_sync.status_code == 200
    assert late_sync.json()["results"][0]["status"] == "audit_only"
    assert late_sync.json()["results"][0]["outcome"] == "audit_late_recorded"
    assert late_sync.json()["results"][0]["reason"] == "late_sync_mismatch_recorded"

    audit_resp = client.get("/api/audit/", headers=headers)
    assert audit_resp.status_code == 200
    late_entries = [log for log in audit_resp.json() if log["action"] == "late_sync_mismatch"]
    assert late_entries
    details = json.loads(late_entries[0]["details"])
    assert details["short_id"] == "M30003"
    assert details["client_tx_id"] == "m3-sync-003"
    assert details["tap_id"] == tap_id
    assert details["volume_ml"] == 200


def test_search_active_visit_by_guest_phone_or_name(client):
    headers, guest_id, _, _ = _prepare_active_visit(
        client, suffix="91006", card_uid="CARD-M3-006"
    )

    guest_resp = client.get(f"/api/guests/{guest_id}", headers=headers)
    assert guest_resp.status_code == 200
    phone = guest_resp.json()["phone_number"]
    last_name = guest_resp.json()["last_name"]

    by_phone = client.get(f"/api/visits/active/search?q={phone}", headers=headers)
    assert by_phone.status_code == 200
    assert by_phone.json()["status"] == "active"

    by_name = client.get(f"/api/visits/active/search?q={last_name}", headers=headers)
    assert by_name.status_code == 200
    assert by_name.json()["status"] == "active"
