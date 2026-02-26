from decimal import Decimal

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
            "first_name": "M4",
            "patronymic": "Sync",
            "phone_number": f"+1777000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"M4DOC-{suffix}",
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
        json={"name": f"M4 Beer {suffix}", "sell_price_per_liter": 500.0},
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
        json={"display_name": f"Tap M4 {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(f"/api/taps/{tap_id}/keg", headers=headers, json={"keg_id": keg_id})
    assert assign_resp.status_code == 200

    topup = client.post(
        f"/api/guests/{guest_id}/topup",
        headers=headers,
        json={"amount": 500, "payment_method": "cash"},
    )
    assert topup.status_code == 200

    return headers, guest_id, visit_id, tap_id


def test_lock_kept_until_backend_accepts_sync(client):
    headers, _, _, tap_id = _prepare_active_visit(client, suffix="92001", card_uid="CARD-M4-001")
    auth = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M4-001", "tap_id": tap_id},
    )
    assert auth.status_code == 200
    assert auth.json()["visit"]["active_tap_id"] == tap_id
    assert auth.json()["visit"]["lock_set_at"] is not None

    before_sync = client.get("/api/visits/active/by-card/CARD-M4-001", headers=headers)
    assert before_sync.status_code == 200
    assert before_sync.json()["active_tap_id"] == tap_id

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m4-sync-001",
                    "card_uid": "CARD-M4-001",
                    "tap_id": tap_id,
                    "short_id": "A12001",
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

    after_sync = client.get("/api/visits/active/by-card/CARD-M4-001", headers=headers)
    assert after_sync.status_code == 200
    assert after_sync.json()["active_tap_id"] is None


def test_pending_sync_transitions_to_synced_on_successful_sync(client, db_session):
    headers, _, visit_id, tap_id = _prepare_active_visit(client, suffix="92005", card_uid="CARD-M4-005")
    auth = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M4-005", "tap_id": tap_id},
    )
    assert auth.status_code == 200

    pending = (
        db_session.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
        )
        .one()
    )
    pending_pour_id = pending.pour_id
    assert pending.volume_ml == 0
    assert pending.short_id is None

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m4-sync-005",
                    "card_uid": "CARD-M4-005",
                    "tap_id": tap_id,
                    "short_id": "E52005",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 180,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["results"][0]["status"] == "accepted"

    db_session.expire_all()
    resolved = db_session.query(models.Pour).filter(models.Pour.pour_id == pending_pour_id).one()
    assert resolved.sync_status == "synced"
    assert resolved.client_tx_id == "m4-sync-005"
    assert resolved.short_id == "E52005"
    assert resolved.volume_ml == 180
    assert resolved.is_manual_reconcile is False

    pending_after = (
        db_session.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_id,
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
        )
        .count()
    )
    assert pending_after == 0

    pours_resp = client.get("/api/pours/", headers=headers)
    assert pours_resp.status_code == 200
    matched = [row for row in pours_resp.json() if row["short_id"] == "E52005"]
    assert len(matched) == 1
    assert matched[0]["sync_status"] == "synced"


def test_sync_without_authorize_returns_audit_only_and_does_not_write_pour(client, db_session):
    headers, _, visit_id, tap_id = _prepare_active_visit(client, suffix="92006", card_uid="CARD-M4-006")

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m4-sync-006-late",
                    "card_uid": "CARD-M4-006",
                    "tap_id": tap_id,
                    "short_id": "F62006",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 160,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert sync_resp.status_code == 200
    assert sync_resp.json()["results"][0]["status"] == "audit_only"
    assert sync_resp.json()["results"][0]["outcome"] == "audit_late_recorded"
    assert sync_resp.json()["results"][0]["reason"] == "late_sync_mismatch_recorded"

    db_session.expire_all()
    late_pours = (
        db_session.query(models.Pour)
        .filter(models.Pour.visit_id == visit_id, models.Pour.short_id == "F62006")
        .count()
    )
    assert late_pours == 0


def test_manual_reconcile_unlocks_visit_and_is_idempotent(client):
    headers, _, visit_id, tap_id = _prepare_active_visit(client, suffix="92002", card_uid="CARD-M4-002")
    auth = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M4-002", "tap_id": tap_id},
    )
    assert auth.status_code == 200

    payload = {
        "tap_id": tap_id,
        "short_id": "B22002",
        "volume_ml": 250,
        "amount": "125.00",
        "reason": "sync_timeout",
        "comment": "operator entered from controller",
    }
    rec1 = client.post(f"/api/visits/{visit_id}/reconcile-pour", headers=headers, json=payload)
    assert rec1.status_code == 200
    assert rec1.json()["active_tap_id"] is None

    rec2 = client.post(f"/api/visits/{visit_id}/reconcile-pour", headers=headers, json=payload)
    assert rec2.status_code == 200
    assert rec2.json()["active_tap_id"] is None

    pours = client.get("/api/pours/", headers=headers)
    assert pours.status_code == 200
    matched = [p for p in pours.json() if p["short_id"] == "B22002"]
    assert len(matched) == 1
    assert matched[0]["sync_status"] == "reconciled"
    assert matched[0]["is_manual_reconcile"] is True


def test_late_sync_after_manual_reconcile_match_and_mismatch_no_double_charge(client):
    headers, guest_id, visit_id, tap_id = _prepare_active_visit(client, suffix="92003", card_uid="CARD-M4-003")
    auth = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M4-003", "tap_id": tap_id},
    )
    assert auth.status_code == 200

    rec = client.post(
        f"/api/visits/{visit_id}/reconcile-pour",
        headers=headers,
        json={
            "tap_id": tap_id,
            "short_id": "C32003",
            "volume_ml": 100,
            "amount": "50.00",
            "reason": "sync_timeout",
            "comment": "manual close",
        },
    )
    assert rec.status_code == 200

    guest_after_reconcile = client.get(f"/api/guests/{guest_id}", headers=headers).json()
    balance_after_reconcile = Decimal(guest_after_reconcile["balance"])

    late_match = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m4-sync-003-match",
                    "card_uid": "CARD-M4-003",
                    "tap_id": tap_id,
                    "short_id": "C32003",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 100,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert late_match.status_code == 200
    assert late_match.json()["results"][0]["status"] == "audit_only"
    assert late_match.json()["results"][0]["outcome"] == "audit_late_matched"
    assert late_match.json()["results"][0]["reason"] == "late_sync_matched"

    late_mismatch = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "m4-sync-003-mismatch",
                    "card_uid": "CARD-M4-003",
                    "tap_id": tap_id,
                    "short_id": "C39999",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 120,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert late_mismatch.status_code == 200
    assert late_mismatch.json()["results"][0]["status"] == "audit_only"
    assert late_mismatch.json()["results"][0]["outcome"] == "audit_late_recorded"
    assert late_mismatch.json()["results"][0]["reason"] == "late_sync_mismatch_recorded"

    guest_after_late = client.get(f"/api/guests/{guest_id}", headers=headers).json()
    assert Decimal(guest_after_late["balance"]) == balance_after_reconcile

    audit_resp = client.get("/api/audit/", headers=headers)
    assert audit_resp.status_code == 200
    actions = [item["action"] for item in audit_resp.json()]
    assert "late_sync_matched" in actions
    assert "late_sync_mismatch" in actions


def test_sync_conflict_returns_409_and_audits(client):
    headers, _, _, tap_id = _prepare_active_visit(client, suffix="92004", card_uid="CARD-M4-004")
    auth = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": "CARD-M4-004", "tap_id": tap_id},
    )
    assert auth.status_code == 200

    extra_tap = client.post("/api/taps/", headers=headers, json={"display_name": "Tap M4 conflict"})
    assert extra_tap.status_code == 201
    conflict_tap_id = extra_tap.json()["tap_id"]

    beverage_resp = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": "M4 Beer conflict 92004", "sell_price_per_liter": 500.0},
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
                    "client_tx_id": "m4-sync-004",
                    "card_uid": "CARD-M4-004",
                    "tap_id": conflict_tap_id,
                    "short_id": "D42004",
                    "start_ts": "2026-01-01T10:00:00Z",
                    "end_ts": "2026-01-01T10:00:05Z",
                    "volume_ml": 200,
                    "price_cents": 0,
                }
            ]
        },
    )
    assert bad_sync.status_code == 409

    audit_resp = client.get("/api/audit/", headers=headers)
    assert audit_resp.status_code == 200
    assert any(log["action"] == "sync_conflict" for log in audit_resp.json())
