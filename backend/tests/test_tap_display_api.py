from decimal import Decimal

import models


ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _auth_headers(client):
    response = client.post("/api/token", data={"username": "admin", "password": "fake_password"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _display_headers(monkeypatch, token="display-secret"):
    monkeypatch.setenv("DISPLAY_API_KEY", token)
    return {"X-Display-Token": token}


def _upload_media_asset(client, headers, kind, filename):
    response = client.post(
        "/api/media-assets",
        headers=headers,
        files={"file": (filename, ONE_PIXEL_PNG, "image/png")},
        data={"kind": kind},
    )
    assert response.status_code == 201
    return response.json()


def test_display_snapshot_returns_effective_payload_and_etag(client, db_session, monkeypatch, tmp_path):
    headers = _display_headers(monkeypatch)
    monkeypatch.setenv("MEDIA_STORAGE_ROOT", str(tmp_path))
    (tmp_path / "bg.png").write_bytes(ONE_PIXEL_PNG)
    (tmp_path / "logo.png").write_bytes(ONE_PIXEL_PNG)

    background_asset = models.MediaAsset(
        kind="background",
        storage_key="bg.png",
        original_filename="bg.png",
        mime_type="image/png",
        byte_size=len(ONE_PIXEL_PNG),
        checksum_sha256="bg-checksum",
    )
    logo_asset = models.MediaAsset(
        kind="logo",
        storage_key="logo.png",
        original_filename="logo.png",
        mime_type="image/png",
        byte_size=len(ONE_PIXEL_PNG),
        checksum_sha256="logo-checksum",
    )
    beverage = models.Beverage(
        name="Display Lager",
        brewery="Test Brewery",
        style="Lager",
        abv=Decimal("4.8"),
        sell_price_per_liter=Decimal("700.00"),
        description_short="Светлый лагер",
        display_brand_name="Display Brand",
        accent_color="#112233",
        background_asset=background_asset,
        logo_asset=logo_asset,
        text_theme="light",
        price_display_mode_default="per_liter",
    )
    keg = models.Keg(
        beverage=beverage,
        initial_volume_ml=30000,
        current_volume_ml=28000,
        purchase_price=Decimal("12000.00"),
        status="in_use",
    )
    tap = models.Tap(display_name="Tap 1", status="active", keg=keg)
    tap_display_config = models.TapDisplayConfig(
        tap=tap,
        enabled=True,
        idle_instruction="Приложите карту",
        fallback_title="Нет назначения",
        fallback_subtitle="Обратитесь к оператору",
        maintenance_title="Сервис",
        maintenance_subtitle="Подождите",
        override_accent_color="#445566",
        show_price_mode="per_100ml",
    )
    db_session.add_all([background_asset, logo_asset, beverage, keg, tap, tap_display_config])
    db_session.commit()

    response = client.get(f"/api/display/taps/{tap.tap_id}/snapshot", headers=headers)
    assert response.status_code == 200
    assert response.headers["etag"]

    payload = response.json()
    assert payload["tap"]["tap_id"] == tap.tap_id
    assert payload["tap"]["enabled"] is True
    assert payload["assignment"]["has_assignment"] is True
    assert "copy" in payload
    assert "copy_block" not in payload
    assert payload["presentation"]["name"] == "Display Lager"
    assert payload["presentation"]["brand_name"] == "Display Brand"
    assert payload["pricing"]["display_mode"] == "per_100ml"
    assert payload["pricing"]["price_per_100ml_cents"] == 7000
    assert payload["theme"]["accent_color"] == "#445566"
    assert payload["theme"]["background_asset"]["checksum_sha256"] == "bg-checksum"
    assert payload["theme"]["logo_asset"]["checksum_sha256"] == "logo-checksum"

    second = client.get(
        f"/api/display/taps/{tap.tap_id}/snapshot",
        headers={**headers, "If-None-Match": response.headers["etag"]},
    )
    assert second.status_code == 304

    rejected = client.get(
        f"/api/display/taps/{tap.tap_id}/snapshot",
        headers={"X-Internal-Token": "demo-secret-key"},
    )
    assert rejected.status_code == 401


def test_media_asset_upload_list_and_content(client, monkeypatch, tmp_path):
    headers = _auth_headers(client)
    display_headers = _display_headers(monkeypatch)
    monkeypatch.setenv("MEDIA_STORAGE_ROOT", str(tmp_path))

    upload = client.post(
        "/api/media-assets",
        headers=headers,
        files={"file": ("hero.png", ONE_PIXEL_PNG, "image/png")},
        data={"kind": "background"},
    )
    assert upload.status_code == 201
    payload = upload.json()
    asset_id = payload["asset_id"]
    assert payload["kind"] == "background"
    assert payload["byte_size"] == len(ONE_PIXEL_PNG)
    assert payload["mime_type"] == "image/png"
    assert payload["width"] == 1
    assert payload["height"] == 1

    listed = client.get("/api/media-assets", headers=headers)
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert len(listed_payload) == 1
    assert listed_payload[0]["asset_id"] == asset_id

    content = client.get(f"/api/media-assets/{asset_id}/content", headers=display_headers)
    assert content.status_code == 200
    assert content.content == ONE_PIXEL_PNG
    assert content.headers["etag"]

    not_modified = client.get(
        f"/api/media-assets/{asset_id}/content",
        headers={**display_headers, "If-None-Match": content.headers["etag"]},
    )
    assert not_modified.status_code == 304

    readonly_upload = client.post(
        "/api/media-assets",
        headers=display_headers,
        files={"file": ("hero.png", ONE_PIXEL_PNG, "image/png")},
        data={"kind": "background"},
    )
    assert readonly_upload.status_code == 401


def test_media_asset_upload_rejects_invalid_kind_mime_and_extension(client, monkeypatch, tmp_path):
    headers = _auth_headers(client)
    monkeypatch.setenv("MEDIA_STORAGE_ROOT", str(tmp_path))

    bad_kind = client.post(
        "/api/media-assets",
        headers=headers,
        files={"file": ("hero.png", ONE_PIXEL_PNG, "image/png")},
        data={"kind": "video"},
    )
    assert bad_kind.status_code == 422

    bad_mime = client.post(
        "/api/media-assets",
        headers=headers,
        files={"file": ("hero.png", ONE_PIXEL_PNG, "image/jpeg")},
        data={"kind": "background"},
    )
    assert bad_mime.status_code == 422

    bad_extension = client.post(
        "/api/media-assets",
        headers=headers,
        files={"file": ("hero.gif", ONE_PIXEL_PNG, "image/png")},
        data={"kind": "background"},
    )
    assert bad_extension.status_code == 422


def test_missing_media_asset_file_is_handled_without_breaking_snapshot(client, db_session, monkeypatch, tmp_path):
    headers = _display_headers(monkeypatch)
    monkeypatch.setenv("MEDIA_STORAGE_ROOT", str(tmp_path))

    missing_asset = models.MediaAsset(
        kind="background",
        storage_key="missing.png",
        original_filename="missing.png",
        mime_type="image/png",
        byte_size=len(ONE_PIXEL_PNG),
        checksum_sha256="missing-checksum",
    )
    beverage = models.Beverage(
        name="Missing Asset Lager",
        brewery="Test Brewery",
        style="Lager",
        abv=Decimal("4.8"),
        sell_price_per_liter=Decimal("700.00"),
        background_asset=missing_asset,
    )
    keg = models.Keg(
        beverage=beverage,
        initial_volume_ml=30000,
        current_volume_ml=28000,
        purchase_price=Decimal("12000.00"),
        status="in_use",
    )
    tap = models.Tap(display_name="Tap Missing Asset", status="active", keg=keg)
    db_session.add_all([missing_asset, beverage, keg, tap])
    db_session.commit()

    snapshot = client.get(f"/api/display/taps/{tap.tap_id}/snapshot", headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["theme"]["background_asset"] is None

    content = client.get(f"/api/media-assets/{missing_asset.asset_id}/content", headers=headers)
    assert content.status_code == 404


def test_beverage_update_and_tap_display_config_endpoints(client):
    headers = _auth_headers(client)

    beverage_response = client.post(
        "/api/beverages/",
        headers=headers,
        json={
            "name": "Update Lager",
            "brewery": "Update Brewery",
            "style": "Lager",
            "abv": "5.0",
            "sell_price_per_liter": "650.00",
        },
    )
    assert beverage_response.status_code == 201
    beverage_id = beverage_response.json()["beverage_id"]

    update_response = client.put(
        f"/api/beverages/{beverage_id}",
        headers=headers,
        json={
            "description_short": "Короткое описание",
            "display_brand_name": "Новый бренд",
            "accent_color": "#AA5500",
            "price_display_mode_default": "per_100ml",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["display_brand_name"] == "Новый бренд"
    assert updated["description_short"] == "Короткое описание"

    tap_response = client.post("/api/taps/", headers=headers, json={"display_name": "Tap Config"})
    assert tap_response.status_code == 201
    tap_id = tap_response.json()["tap_id"]

    config_put = client.put(
        f"/api/taps/{tap_id}/display-config",
        headers=headers,
        json={
            "enabled": False,
            "idle_instruction": "Поднесите карту",
            "fallback_title": "Пусто",
            "maintenance_title": "Мойка",
            "show_price_mode": "per_liter",
        },
    )
    assert config_put.status_code == 200
    config_payload = config_put.json()
    assert config_payload["enabled"] is False
    assert config_payload["idle_instruction"] == "Поднесите карту"
    assert config_payload["show_price_mode"] == "per_liter"

    config_get = client.get(f"/api/taps/{tap_id}/display-config", headers=headers)
    assert config_get.status_code == 200
    assert config_get.json()["fallback_title"] == "Пусто"


def test_admin_content_workflow_updates_snapshot_with_media_and_tap_overrides(client, monkeypatch, tmp_path):
    headers = _auth_headers(client)
    display_headers = _display_headers(monkeypatch)
    monkeypatch.setenv("MEDIA_STORAGE_ROOT", str(tmp_path))

    beverage_background = _upload_media_asset(client, headers, "background", "beverage-bg.png")
    beverage_logo = _upload_media_asset(client, headers, "logo", "beverage-logo.png")
    tap_background = _upload_media_asset(client, headers, "background", "tap-bg.png")

    beverage_response = client.post(
        "/api/beverages/",
        headers=headers,
        json={
            "name": "MVP Lager",
            "brewery": "North Brewery",
            "style": "Lager",
            "abv": "4.7",
            "sell_price_per_liter": "650.00",
        },
    )
    assert beverage_response.status_code == 201
    beverage_id = beverage_response.json()["beverage_id"]

    beverage_update = client.put(
        f"/api/beverages/{beverage_id}",
        headers=headers,
        json={
            "display_brand_name": "Guest Brand",
            "description_short": "Свежий лагер с мягкой горчинкой",
            "accent_color": "#123456",
            "text_theme": "light",
            "price_display_mode_default": "per_liter",
            "background_asset_id": beverage_background["asset_id"],
            "logo_asset_id": beverage_logo["asset_id"],
        },
    )
    assert beverage_update.status_code == 200
    beverage_payload = beverage_update.json()
    assert beverage_payload["background_asset_id"] == beverage_background["asset_id"]
    assert beverage_payload["logo_asset_id"] == beverage_logo["asset_id"]
    assert beverage_payload["text_theme"] == "light"

    keg_response = client.post(
        "/api/kegs/",
        headers=headers,
        json={
            "beverage_id": beverage_id,
            "initial_volume_ml": 30000,
            "purchase_price": "12000.00",
        },
    )
    assert keg_response.status_code == 201
    keg_id = keg_response.json()["keg_id"]

    tap_response = client.post("/api/taps/", headers=headers, json={"display_name": "Tap MVP"})
    assert tap_response.status_code == 201
    tap_id = tap_response.json()["tap_id"]

    assign_response = client.put(
        f"/api/taps/{tap_id}/keg",
        headers=headers,
        json={"keg_id": keg_id},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["keg"]["beverage"]["beverage_id"] == beverage_id

    config_response = client.put(
        f"/api/taps/{tap_id}/display-config",
        headers=headers,
        json={
            "enabled": True,
            "fallback_title": "Кран пока пуст",
            "fallback_subtitle": "Скоро подключим новый сорт",
            "maintenance_title": "Идет обслуживание",
            "maintenance_subtitle": "Пожалуйста, подождите",
            "override_accent_color": "#654321",
            "override_background_asset_id": tap_background["asset_id"],
            "show_price_mode": "per_100ml",
        },
    )
    assert config_response.status_code == 200
    config_payload = config_response.json()
    assert config_payload["override_background_asset_id"] == tap_background["asset_id"]
    assert config_payload["show_price_mode"] == "per_100ml"

    snapshot_response = client.get(f"/api/display/taps/{tap_id}/snapshot", headers=display_headers)
    assert snapshot_response.status_code == 200

    snapshot = snapshot_response.json()
    assert snapshot["presentation"]["name"] == "MVP Lager"
    assert snapshot["presentation"]["brand_name"] == "Guest Brand"
    assert snapshot["presentation"]["description_short"] == "Свежий лагер с мягкой горчинкой"
    assert snapshot["pricing"]["display_mode"] == "per_100ml"
    assert snapshot["theme"]["accent_color"] == "#654321"
    assert snapshot["theme"]["text_theme"] == "light"
    assert snapshot["theme"]["background_asset"]["asset_id"] == tap_background["asset_id"]
    assert snapshot["theme"]["logo_asset"]["asset_id"] == beverage_logo["asset_id"]
    assert "copy" in snapshot
    assert "copy_block" not in snapshot
    assert snapshot["copy"]["fallback_title"] == "Кран пока пуст"
    assert snapshot["copy"]["fallback_subtitle"] == "Скоро подключим новый сорт"
    assert snapshot["copy"]["maintenance_title"] == "Идет обслуживание"
    assert snapshot["copy"]["maintenance_subtitle"] == "Пожалуйста, подождите"
