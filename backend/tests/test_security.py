def test_unauthorized_access_to_protected_route(client):
    response = client.get('/api/kegs/')
    assert response.status_code == 401
    assert response.json() == {'detail': 'Could not validate credentials'}


def _flow_event_payload():
    return {
        "event_id": "security-check-1",
        "event_status": "started",
        "tap_id": 1,
        "volume_ml": 10,
        "duration_ms": 100,
        "card_present": False,
        "valve_open": False,
        "session_state": "authorized_session",
        "reason": "authorized_pour_in_progress",
    }


def test_internal_token_is_rejected_on_admin_routes(client):
    response = client.get('/api/guests', headers={'X-Internal-Token': 'demo-secret-key'})
    assert response.status_code == 401


def test_internal_token_with_quotes_is_accepted_on_internal_route(client, monkeypatch):
    monkeypatch.setenv('INTERNAL_API_KEY', '"demo-secret-key"')
    response = client.post('/api/controllers/flow-events', headers={'X-Internal-Token': 'demo-secret-key'}, json=_flow_event_payload())
    assert response.status_code == 202


def test_demo_internal_token_still_works_on_internal_route_when_enabled(client, monkeypatch):
    monkeypatch.setenv('INTERNAL_API_KEY', 'my-prod-key')
    monkeypatch.setenv('ALLOW_LEGACY_DEMO_INTERNAL_TOKEN', 'true')
    response = client.post('/api/controllers/flow-events', headers={'X-Internal-Token': 'demo-secret-key'}, json=_flow_event_payload())
    assert response.status_code == 202
