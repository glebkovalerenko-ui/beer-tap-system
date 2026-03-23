from datetime import date
from decimal import Decimal

import models


def _login(client):
    response = client.post('/api/token', data={'username': 'admin', 'password': 'fake_password'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_incidents_and_system_summary(client, db_session):
    headers = _login(client)

    beverage = models.Beverage(name='Incident Beer', sell_price_per_liter=Decimal('300.00'))
    keg = models.Keg(beverage=beverage, initial_volume_ml=5000, current_volume_ml=5000, purchase_price=Decimal('1200.00'), status='in_use')
    tap = models.Tap(tap_id=21, display_name='Incident Tap', status='active', keg=keg)
    db_session.add_all([beverage, keg, tap, models.SystemState(key='emergency_stop_enabled', value='true')])
    db_session.commit()

    response = client.post(
        '/api/controllers/flow-events',
        headers={'X-Internal-Token': 'demo-secret-key'},
        json={
            'event_id': 'incident-21-1',
            'event_status': 'started',
            'tap_id': 21,
            'volume_ml': 25,
            'duration_ms': 900,
            'card_present': False,
            'valve_open': False,
            'session_state': 'no_card_no_session',
            'card_uid': None,
            'short_id': None,
            'reason': 'flow_detected_when_valve_closed_without_active_session',
        },
    )
    assert response.status_code == 202

    incidents = client.get('/api/incidents/', headers=headers)
    assert incidents.status_code == 200
    payload = incidents.json()
    assert any(item['type'] == 'emergency_stop' for item in payload)
    assert any(item['type'] == 'closed_valve_flow' for item in payload)

    summary = client.get('/api/system/status', headers=headers)
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload['emergency_stop'] is True
    assert any(item['name'] == 'controllers' for item in summary_payload['subsystems'])


def test_incident_mutation_endpoints_persist_overlay_and_audit(client, db_session):
    headers = _login(client)

    beverage = models.Beverage(name='Incident Beer Mutable', sell_price_per_liter=Decimal('320.00'))
    keg = models.Keg(beverage=beverage, initial_volume_ml=5000, current_volume_ml=5000, purchase_price=Decimal('900.00'), status='in_use')
    tap = models.Tap(tap_id=31, display_name='Mutable Incident Tap', status='active', keg=keg)
    db_session.add_all([beverage, keg, tap])
    db_session.commit()

    response = client.post(
        '/api/controllers/flow-events',
        headers={'X-Internal-Token': 'demo-secret-key'},
        json={
            'event_id': 'incident-31-1',
            'event_status': 'started',
            'tap_id': 31,
            'volume_ml': 40,
            'duration_ms': 1000,
            'card_present': False,
            'valve_open': False,
            'session_state': 'no_card_no_session',
            'card_uid': None,
            'short_id': None,
            'reason': 'flow_detected_when_valve_closed_without_active_session',
        },
    )
    assert response.status_code == 202

    incident_id = 'flow-incident-31-1'

    claim = client.post(f'/api/incidents/{incident_id}/claim', headers=headers, json={'owner': 'Shift Lead', 'note': 'Принял в работу'})
    assert claim.status_code == 200
    assert claim.json()['owner'] == 'Shift Lead'
    assert claim.json()['status'] == 'in_progress'

    note = client.post(f'/api/incidents/{incident_id}/notes', headers=headers, json={'note': 'Проверил клапан и логи'})
    assert note.status_code == 200
    assert note.json()['note_action'] == 'Проверил клапан и логи'
    assert note.json()['last_action'] == 'note'

    escalate = client.post(f'/api/incidents/{incident_id}/escalate', headers=headers, json={'reason': 'Нужна инженерная проверка датчика', 'note': 'Передал инженеру'})
    assert escalate.status_code == 200
    assert escalate.json()['escalation_reason'] == 'Нужна инженерная проверка датчика'
    assert escalate.json()['escalated_at'] is not None

    close = client.post(f'/api/incidents/{incident_id}/close', headers=headers, json={'resolution_summary': 'Заменили датчик потока', 'note': 'Подтверждено контрольным проливом'})
    assert close.status_code == 200
    payload = close.json()
    assert payload['status'] == 'closed'
    assert payload['closed_at'] is not None
    assert payload['closure_summary'] == 'Заменили датчик потока'

    db_session.expire_all()
    overlay = db_session.query(models.IncidentState).filter(models.IncidentState.incident_id == incident_id).one()
    assert overlay.owner == 'Shift Lead'
    assert overlay.last_note == 'Подтверждено контрольным проливом'
    assert overlay.escalation_reason == 'Нужна инженерная проверка датчика'
    assert overlay.closure_summary == 'Заменили датчик потока'
    assert overlay.closed_at is not None

    audit_actions = [row.action for row in db_session.query(models.AuditLog).filter(models.AuditLog.target_id == incident_id).all()]
    assert 'incident_claim' in audit_actions
    assert 'incident_note' in audit_actions
    assert 'incident_escalate' in audit_actions
    assert 'incident_close' in audit_actions
