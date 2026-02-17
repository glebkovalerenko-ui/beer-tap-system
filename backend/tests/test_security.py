def test_unauthorized_access_to_protected_route(client):
    """
    Проверяем, что защищенный эндпоинт (`/api/kegs/`) возвращает ошибку 401 Unauthorized
    при попытке доступа без JWT-токена.

    Этот тест подтверждает, что наша система безопасности и фикстура `client` работают.
    """
    response = client.get("/api/kegs/")
    assert response.status_code == 401
<<<<<<< codex/conduct-full-repository-audit-1z5eur
    assert response.json() == {"detail": "Could not validate credentials"}


def test_internal_token_allows_guest_list_access(client):
    """RPi-контроллер должен иметь доступ к списку гостей по internal token."""
    response = client.get("/api/guests", headers={"X-Internal-Token": "demo-secret-key"})
    assert response.status_code == 200
=======
    
    # 3. (Опционально, но рекомендуется) Проверяем тело ответа, чтобы быть
    #    уверенными, что это именно та ошибка, которую мы ожидаем.
    assert response.json() == {"detail": "Could not validate credentials"}
>>>>>>> master
