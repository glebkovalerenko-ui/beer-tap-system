from fastapi.testclient import TestClient


def _token(client: TestClient, username: str) -> str:
    response = client.post("/api/token", data={"username": username, "password": "fake_password"})
    assert response.status_code == 200
    return response.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_me_exposes_role_and_permissions(client: TestClient):
    token = _token(client, "shift_lead")

    response = client.get("/api/me", headers=_headers(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "shift_lead"
    assert "incidents_manage" in payload["permissions"]
    assert "system_engineering_actions" not in payload["permissions"]


def test_operator_cannot_set_emergency_stop(client: TestClient):
    token = _token(client, "operator")

    response = client.post(
        "/api/system/emergency_stop",
        headers=_headers(token),
        json={"value": "true"},
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["reason"] == "forbidden"
    assert "maintenance_actions" in detail["missing_permissions"]


def test_shift_lead_can_set_emergency_stop(client: TestClient):
    token = _token(client, "shift_lead")

    response = client.post(
        "/api/system/emergency_stop",
        headers=_headers(token),
        json={"value": "true"},
    )

    assert response.status_code == 200
    assert response.json()["emergency_stop"] is True
