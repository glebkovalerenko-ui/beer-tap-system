
def _login(client):
    response = client.post('/api/token', data={'username': 'admin', 'password': 'fake_password'})
    assert response.status_code == 200
    headers = {'Authorization': f"Bearer {response.json()['access_token']}"}
    shift_open = client.post('/api/shifts/open', headers=headers)
    assert shift_open.status_code in (200, 409)
    return headers


def test_session_history_returns_active_and_detail(client):
    headers = _login(client)
    guest_resp = client.post(
        '/api/guests/',
        headers=headers,
        json={
            'last_name': 'History',
            'first_name': 'Guest',
            'patronymic': 'T',
            'phone_number': '+79990001122',
            'date_of_birth': '1990-01-01',
            'id_document': 'HIST-001',
        },
    )
    assert guest_resp.status_code == 201
    guest_id = guest_resp.json()['guest_id']

    open_resp = client.post('/api/visits/open', headers=headers, json={'guest_id': guest_id})
    assert open_resp.status_code == 200
    visit_id = open_resp.json()['visit_id']

    history_resp = client.get('/api/visits/history', headers=headers)
    assert history_resp.status_code == 200
    rows = history_resp.json()
    match = next(item for item in rows if item['visit_id'] == visit_id)
    assert match['guest_full_name'].startswith('History Guest')
    assert match['visit_status'] == 'active'
    assert 'lifecycle' in match

    detail_resp = client.get(f'/api/visits/history/{visit_id}', headers=headers)
    assert detail_resp.status_code == 200
    payload = detail_resp.json()
    assert payload['visit_id'] == visit_id
    assert payload['narrative'][0]['kind'] == 'open'
