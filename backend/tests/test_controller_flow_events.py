import json

import models


def test_controller_flow_event_is_written_to_audit_log(client, db_session):
    response = client.post(
        "/api/controllers/flow-events",
        headers={"X-Internal-Token": "demo-secret-key"},
        json={
            "tap_id": 7,
            "volume_ml": 12,
            "duration_ms": 1400,
            "card_present": False,
            "session_state": "no_card_no_session",
            "reason": "flow_detected_when_valve_closed_without_active_session",
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True

    audit = (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.action == "controller_flow_anomaly", models.AuditLog.target_id == "7")
        .one()
    )
    details = json.loads(audit.details)
    assert details["tap_id"] == 7
    assert details["volume_ml"] == 12
    assert details["session_state"] == "no_card_no_session"
