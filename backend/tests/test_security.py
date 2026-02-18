def test_unauthorized_access_to_protected_route(client):
    response = client.get('/api/kegs/')
    assert response.status_code == 401
    assert response.json() == {'detail': 'Could not validate credentials'}


def test_internal_token_allows_guest_list_access(client):
    response = client.get('/api/guests', headers={'X-Internal-Token': 'demo-secret-key'})
    assert response.status_code == 200


def test_internal_token_with_quotes_is_accepted(client, monkeypatch):
    monkeypatch.setenv('INTERNAL_API_KEY', '"demo-secret-key"')
    response = client.get('/api/guests', headers={'X-Internal-Token': 'demo-secret-key'})
    assert response.status_code == 200


def test_demo_internal_token_works_even_when_primary_key_differs(client, monkeypatch):
    monkeypatch.setenv('INTERNAL_API_KEY', 'my-prod-key')
    monkeypatch.setenv('ALLOW_LEGACY_DEMO_INTERNAL_TOKEN', 'true')
    response = client.get('/api/guests', headers={'X-Internal-Token': 'demo-secret-key'})
    assert response.status_code == 200
