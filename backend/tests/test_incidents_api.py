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
