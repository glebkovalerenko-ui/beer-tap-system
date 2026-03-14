import importlib.util
import json
import sys
import types
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path


def _load_agent_modules():
    agent_dir = Path(__file__).resolve().parent
    config_path = agent_dir / "config.py"
    service_path = agent_dir / "service.py"

    class DummyRequestException(Exception):
        pass

    class DummySession:
        def get(self, *args, **kwargs):
            raise NotImplementedError

    requests_stub = types.SimpleNamespace(
        Session=DummySession,
        RequestException=DummyRequestException,
    )

    sys.modules["requests"] = requests_stub

    config_spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(config_spec)
    sys.modules["config"] = config_module
    config_spec.loader.exec_module(config_module)

    service_spec = importlib.util.spec_from_file_location("tap_display_agent_service_test", service_path)
    service_module = importlib.util.module_from_spec(service_spec)
    service_spec.loader.exec_module(service_module)

    return config_module, service_module, DummyRequestException


config_module, service_module, DummyRequestException = _load_agent_modules()
AgentConfig = config_module.AgentConfig
DisplayAgentService = service_module.DisplayAgentService


class FakeResponse:
    def __init__(self, *, status_code, headers=None, payload=None, content=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload
        self.content = content

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise DummyRequestException(f"http_{self.status_code}")


class FakeSession:
    def __init__(self, *, snapshot_payload, etag, background_bytes, logo_bytes):
        self.snapshot_payload = snapshot_payload
        self.etag = etag
        self.background_bytes = background_bytes
        self.logo_bytes = logo_bytes
        self.snapshot_request_headers = []

    def get(self, url, headers=None, timeout=10):
        del timeout
        path = urlsplit(url).path
        request_headers = headers or {}

        if path.startswith("/api/display/taps/"):
            self.snapshot_request_headers.append(dict(request_headers))
            if request_headers.get("If-None-Match") == self.etag:
                return FakeResponse(status_code=304, headers={"ETag": self.etag})
            return FakeResponse(
                status_code=200,
                headers={"ETag": self.etag},
                payload=self.snapshot_payload,
            )

        if path.endswith("/background/content"):
            return FakeResponse(status_code=200, content=self.background_bytes)

        if path.endswith("/logo/content"):
            return FakeResponse(status_code=200, content=self.logo_bytes)

        raise AssertionError(f"Unexpected URL requested: {url}")


def test_display_agent_polls_snapshot_caches_assets_and_reads_runtime(tmp_path):
    runtime_path = tmp_path / "display-runtime.json"
    cache_dir = tmp_path / "cache"
    etag = '"content-v2"'
    snapshot_payload = {
        "tap": {
            "tap_id": 7,
            "enabled": True,
            "status": "active",
        },
        "assignment": {
            "has_assignment": True,
        },
        "presentation": {
            "name": "Smoke Lager",
        },
        "pricing": {
            "display_text": "65 RUB / 100 ml",
        },
        "theme": {
            "background_asset": {
                "asset_id": "background",
                "checksum_sha256": "bg-sha",
                "content_url": "/api/media-assets/background/content",
            },
            "logo_asset": {
                "asset_id": "logo",
                "checksum_sha256": "logo-sha",
                "content_url": "/api/media-assets/logo/content",
            },
        },
        "copy": {
            "idle_instruction": "Tap card to pour",
        },
        "content_version": "content-v2",
    }

    service = DisplayAgentService(
        AgentConfig(
            tap_id=7,
            backend_url="http://backend.local",
            display_token="display-secret",
            runtime_path=runtime_path,
            cache_dir=cache_dir,
            client_dist_dir=tmp_path / "dist",
            poll_interval_seconds=5,
            backend_lost_after_seconds=15,
            backend_lost_failures=2,
            runtime_stale_after_seconds=3,
            host="127.0.0.1",
            port=18181,
        )
    )
    service.session = FakeSession(
        snapshot_payload=snapshot_payload,
        etag=etag,
        background_bytes=b"background-bytes",
        logo_bytes=b"logo-bytes",
    )

    service.poll_once()

    assert service.state.etag == etag
    assert service.state.snapshot["theme"]["background_asset"]["content_url"].startswith("/local/display/assets/background")
    assert service.state.snapshot["theme"]["logo_asset"]["content_url"].startswith("/local/display/assets/logo")
    assert set(service.state.asset_files) == {"background", "logo"}
    assert service.snapshot_cache_path.exists()
    assert service.state_cache_path.exists()

    service.poll_once()

    assert len(service.session.snapshot_request_headers) == 2
    assert service.session.snapshot_request_headers[1]["If-None-Match"] == etag
    assert service.state.consecutive_failures == 0

    runtime_payload = {
        "schema_version": 1,
        "tap_id": 7,
        "phase": "pouring",
        "reason_code": None,
        "card_present": True,
        "guest_first_name": "Ivan",
        "current_volume_ml": 320,
        "current_cost_cents": 2240,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    runtime_path.write_text(json.dumps(runtime_payload), encoding="utf-8")

    payload = service.read_runtime_payload()

    assert payload["runtime"]["phase"] == "pouring"
    assert payload["runtime"]["current_volume_ml"] == 320
    assert payload["health"]["backend_link_lost"] is False
    assert payload["health"]["controller_runtime_stale"] is False
