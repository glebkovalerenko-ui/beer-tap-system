import uuid
from datetime import datetime, timezone
from decimal import Decimal

import models


def _auth_headers(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    shift_open = client.post("/api/shifts/open", headers=headers)
    assert shift_open.status_code in (200, 409)
    return headers


def _seed_guest_visit_and_tap(client, headers, suffix: str):
    guest_resp = client.post(
        "/api/guests/",
        headers=headers,
        json={
            "last_name": f"M7{suffix}",
            "first_name": "Guest",
            "patronymic": "POS",
            "phone_number": f"+1777200{suffix}",
            "date_of_birth": "1990-01-15",
            "id_document": f"M7-POS-{suffix}",
        },
    )
    assert guest_resp.status_code == 201
    guest_id = guest_resp.json()["guest_id"]

    card_uid = f"M7-CARD-{suffix}"
    bind_resp = client.post(
        f"/api/guests/{guest_id}/cards",
        headers=headers,
        json={"card_uid": card_uid},
    )
    assert bind_resp.status_code == 200

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
        json={"name": f"M7 Beer {suffix}", "sell_price_per_liter": 400.0},
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
        json={"display_name": f"M7 Tap {suffix}"},
    )
    assert tap_resp.status_code == 201
    tap_id = tap_resp.json()["tap_id"]

    assign_resp = client.put(
        f"/api/taps/{tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_id},
    )
    assert assign_resp.status_code == 200

    return {
        "guest_id": guest_id,
        "visit_id": visit_id,
        "card_uid": card_uid,
        "tap_id": tap_id,
        "keg_id": keg_id,
    }


def _count_audit(db_session, action: str) -> int:
    return db_session.query(models.AuditLog).filter(models.AuditLog.action == action).count()


def test_fifo_suggestion_endpoint_uses_oldest_created_at_then_keg_id(client, db_session):
    headers = _auth_headers(client)

    beer_type_id = uuid.uuid4()
    db_session.add(
        models.Beverage(
            beverage_id=beer_type_id,
            name="M7 FIFO Lager",
            sell_price_per_liter=Decimal("350.00"),
        )
    )
    db_session.add_all(
        [
            models.Keg(
                keg_id=uuid.UUID("00000000-0000-0000-0000-00000000010b"),
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=30000,
                purchase_price=Decimal("1000.00"),
                status="full",
                created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
            ),
            models.Keg(
                keg_id=uuid.UUID("00000000-0000-0000-0000-00000000010a"),
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=30000,
                purchase_price=Decimal("1000.00"),
                status="full",
                created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
            ),
            models.Keg(
                keg_id=uuid.UUID("00000000-0000-0000-0000-00000000020a"),
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=30000,
                purchase_price=Decimal("1000.00"),
                status="full",
                created_at=datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/kegs/suggest?beer_type_id={beer_type_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["candidates_count"] == 3
    assert body["reason"] == "oldest_available"
    assert body["ordering_keys_used"] == ["created_at", "keg_id"]
    assert body["recommended_keg"]["keg_id"] == "00000000-0000-0000-0000-00000000010a"


def test_fifo_suggestion_excludes_ineligible_kegs(client, db_session):
    headers = _auth_headers(client)

    beer_type_id = uuid.uuid4()
    eligible_keg_id = uuid.uuid4()
    assigned_keg_id = uuid.uuid4()
    empty_keg_id = uuid.uuid4()
    zero_volume_keg_id = uuid.uuid4()

    db_session.add(
        models.Beverage(
            beverage_id=beer_type_id,
            name="M7 FIFO IPA",
            sell_price_per_liter=Decimal("420.00"),
        )
    )
    db_session.add_all(
        [
            models.Keg(
                keg_id=eligible_keg_id,
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=30000,
                purchase_price=Decimal("1000.00"),
                status="full",
                created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
            ),
            models.Keg(
                keg_id=assigned_keg_id,
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=30000,
                purchase_price=Decimal("1000.00"),
                status="in_use",
                created_at=datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc),
            ),
            models.Keg(
                keg_id=empty_keg_id,
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=0,
                purchase_price=Decimal("1000.00"),
                status="empty",
                created_at=datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc),
            ),
            models.Keg(
                keg_id=zero_volume_keg_id,
                beverage_id=beer_type_id,
                initial_volume_ml=30000,
                current_volume_ml=0,
                purchase_price=Decimal("1000.00"),
                status="full",
                created_at=datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc),
            ),
            models.Tap(
                tap_id=77,
                display_name="M7 Occupied Tap",
                status="active",
                keg_id=assigned_keg_id,
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/kegs/suggest?beer_type_id={beer_type_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["candidates_count"] == 1
    assert body["recommended_keg"]["keg_id"] == str(eligible_keg_id)


def test_pos_stub_emits_topup_refund_and_final_pour_without_duplicates(client, db_session):
    headers = _auth_headers(client)
    seeded = _seed_guest_visit_and_tap(client, headers, suffix="97011")

    topup_resp = client.post(
        f"/api/guests/{seeded['guest_id']}/topup",
        headers=headers,
        json={"amount": 50.0, "payment_method": "cash"},
    )
    assert topup_resp.status_code == 200
    assert _count_audit(db_session, "pos_stub_topup_notified") == 1

    refund_resp = client.post(
        f"/api/guests/{seeded['guest_id']}/refund",
        headers=headers,
        json={"amount": 5.0, "payment_method": "cash", "reason": "demo_refund"},
    )
    assert refund_resp.status_code == 200
    assert _count_audit(db_session, "pos_stub_refund_notified") == 1

    authorize_resp = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": seeded["card_uid"], "tap_id": seeded["tap_id"]},
    )
    assert authorize_resp.status_code == 200

    sync_payload = {
        "pours": [
            {
                "client_tx_id": "m7-sync-97011",
                "card_uid": seeded["card_uid"],
                "tap_id": seeded["tap_id"],
                "short_id": "M797011",
                "duration_ms": 3000,
                "volume_ml": 100,
                "price_cents": 40,
            }
        ]
    }
    sync_resp = client.post("/api/sync/pours", json=sync_payload)
    assert sync_resp.status_code == 200
    assert _count_audit(db_session, "pos_stub_pour_notified") == 1

    duplicate_sync_resp = client.post("/api/sync/pours", json=sync_payload)
    assert duplicate_sync_resp.status_code == 200
    assert _count_audit(db_session, "pos_stub_pour_notified") == 1


def test_pos_stub_does_not_duplicate_after_manual_reconcile_and_late_sync(client, db_session):
    headers = _auth_headers(client)
    seeded = _seed_guest_visit_and_tap(client, headers, suffix="97012")

    topup_resp = client.post(
        f"/api/guests/{seeded['guest_id']}/topup",
        headers=headers,
        json={"amount": 50.0, "payment_method": "cash"},
    )
    assert topup_resp.status_code == 200

    authorize_resp = client.post(
        "/api/visits/authorize-pour",
        headers=headers,
        json={"card_uid": seeded["card_uid"], "tap_id": seeded["tap_id"]},
    )
    assert authorize_resp.status_code == 200

    reconcile_resp = client.post(
        f"/api/visits/{seeded['visit_id']}/reconcile-pour",
        headers=headers,
        json={
            "tap_id": seeded["tap_id"],
            "short_id": "M797012",
            "volume_ml": 120,
            "amount": "48.00",
            "duration_ms": 3200,
            "reason": "controller_timeout",
            "comment": "manual for m7",
        },
    )
    assert reconcile_resp.status_code == 200
    assert _count_audit(db_session, "pos_stub_pour_notified") == 1

    late_sync_resp = client.post(
        "/api/sync/pours",
        json={
            "pours": [
                {
                    "client_tx_id": "m7-late-97012",
                    "card_uid": seeded["card_uid"],
                    "tap_id": seeded["tap_id"],
                    "short_id": "M797012",
                    "duration_ms": 3200,
                    "volume_ml": 120,
                    "price_cents": 40,
                }
            ]
        },
    )
    assert late_sync_resp.status_code == 200
    assert _count_audit(db_session, "pos_stub_pour_notified") == 1
