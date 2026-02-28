import json
import uuid

import models
from sqlalchemy import func


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
            "last_name": f"Incident{suffix}",
            "first_name": "Zero",
            "patronymic": "Balance",
            "phone_number": f"+1555000{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"INCIDENT-{suffix}",
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


def _create_tap_with_keg(client, headers, suffix: str):
    beverage_resp = client.post(
        "/api/beverages/",
        headers=headers,
        json={"name": f"Incident Beer {suffix}", "sell_price_per_liter": 500.0},
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
        json={"display_name": f"Incident Tap {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(f"/api/taps/{tap_id}/keg", headers=headers, json={"keg_id": keg_id})
    assert assign_resp.status_code == 200
    return tap_id


def _prepare_visit(client, headers, suffix: str, *, topup_amount: int | None):
    guest_id = _create_guest(client, headers, suffix=suffix)
    card_uid = f"INCIDENT-CARD-{suffix}"
    _bind_card(client, headers, guest_id, card_uid)
    visit_id = _open_visit(client, headers, guest_id, card_uid)
    tap_id = _create_tap_with_keg(client, headers, suffix=suffix)

    if topup_amount is not None:
        topup = client.post(
            f"/api/guests/{guest_id}/topup",
            headers=headers,
            json={"amount": topup_amount, "payment_method": "cash"},
        )
        assert topup.status_code == 200

    return guest_id, visit_id, card_uid, tap_id


def test_authorize_denies_when_balance_zero(client, db_session):
    headers = _login(client)
    guest_id, visit_id, card_uid, tap_id = _prepare_visit(
        client,
        headers,
        suffix="94001",
        topup_amount=None,
    )

    response = client.post(
        "/api/visits/authorize-pour",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={"card_uid": card_uid, "tap_id": tap_id},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "insufficient_funds"

    db_session.expire_all()
    visit_uuid = uuid.UUID(visit_id)
    visit = db_session.query(models.Visit).filter(models.Visit.visit_id == visit_uuid).one()
    assert str(visit.guest_id) == guest_id
    assert visit.active_tap_id is None
    assert visit.lock_set_at is None

    pending_sync = (
        db_session.query(models.Pour)
        .filter(
            models.Pour.visit_id == visit_uuid,
            models.Pour.tap_id == tap_id,
            models.Pour.sync_status == "pending_sync",
        )
        .count()
    )
    assert pending_sync == 0

    audit = (
        db_session.query(models.AuditLog)
        .filter(
            models.AuditLog.action == "insufficient_funds_denied",
            models.AuditLog.target_id == visit_id,
        )
        .one()
    )
    details = json.loads(audit.details)
    assert details["card_uid"] == card_uid
    assert details["guest_id"] == guest_id
    assert details["visit_id"] == visit_id
    assert details["tap_id"] == tap_id
    assert details["balance"] == "0.00"


def test_sync_without_authorize_returns_audit_only_not_accepted(client, db_session):
    headers = _login(client)
    guest_id, visit_id, card_uid, tap_id = _prepare_visit(
        client,
        headers,
        suffix="94002",
        topup_amount=500,
    )

    visit_uuid = uuid.UUID(visit_id)
    db_session.query(models.Visit).filter(models.Visit.visit_id == visit_uuid).update(
        {
            models.Visit.active_tap_id: tap_id,
            models.Visit.lock_set_at: func.now(),
        }
    )
    db_session.commit()

    sync_resp = client.post(
        "/api/sync/pours",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "pours": [
                {
                    "client_tx_id": "incident-sync-no-pending-001",
                    "card_uid": card_uid,
                    "tap_id": tap_id,
                    "short_id": "NP94002",
                    "duration_ms": 5000,
                    "volume_ml": 200,
                    "price_cents": 0,
                }
            ]
        },
    )

    assert sync_resp.status_code == 200
    result = sync_resp.json()["results"][0]
    assert result["status"] == "audit_only"
    assert result["outcome"] == "audit_missing_pending"
    assert result["reason"] == "missing_pending_authorize"

    db_session.expire_all()
    pours = (
        db_session.query(models.Pour)
        .filter(models.Pour.visit_id == visit_uuid, models.Pour.short_id == "NP94002")
        .count()
    )
    assert pours == 0

    audit = (
        db_session.query(models.AuditLog)
        .filter(
            models.AuditLog.action == "sync_missing_pending",
            models.AuditLog.target_id == visit_id,
        )
        .one()
    )
    details = json.loads(audit.details)
    assert details["card_uid"] == card_uid
    assert details["guest_id"] == guest_id
    assert details["tap_id"] == tap_id
