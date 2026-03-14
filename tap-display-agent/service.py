import json
import logging
import os
import tempfile
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests

from config import AgentConfig


LOGGER = logging.getLogger("tap_display_agent")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        normalized = raw_value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
    ) as temp_file:
        temp_file.write(serialized)
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


@dataclass
class AgentState:
    snapshot: dict[str, Any] | None = None
    etag: str | None = None
    last_success_at: str | None = None
    last_poll_at: str | None = None
    consecutive_failures: int = 0
    asset_files: dict[str, str] = field(default_factory=dict)


class DisplayAgentService:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.session = requests.Session()
        self._backend_headers = {"X-Display-Token": config.display_token}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.cache_dir = config.cache_dir
        self.snapshot_cache_path = self.cache_dir / "snapshot.json"
        self.state_cache_path = self.cache_dir / "state.json"
        self.assets_dir = self.cache_dir / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.state = AgentState()
        self._load_cached_state()

    def _load_cached_state(self) -> None:
        if self.state_cache_path.exists():
            try:
                raw_state = json.loads(self.state_cache_path.read_text(encoding="utf-8"))
                self.state = AgentState(
                    snapshot=None,
                    etag=raw_state.get("etag"),
                    last_success_at=raw_state.get("last_success_at"),
                    last_poll_at=raw_state.get("last_poll_at"),
                    consecutive_failures=int(raw_state.get("consecutive_failures") or 0),
                    asset_files=dict(raw_state.get("asset_files") or {}),
                )
            except (OSError, ValueError, TypeError):
                LOGGER.exception("Failed to load cached display-agent state")

        if self.snapshot_cache_path.exists():
            try:
                self.state.snapshot = json.loads(self.snapshot_cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                LOGGER.exception("Failed to load cached snapshot")

    def _persist_state(self) -> None:
        with self._lock:
            snapshot = deepcopy(self.state.snapshot)
            state_payload = {
                "etag": self.state.etag,
                "last_success_at": self.state.last_success_at,
                "last_poll_at": self.state.last_poll_at,
                "consecutive_failures": self.state.consecutive_failures,
                "asset_files": dict(self.state.asset_files),
            }

        if snapshot is not None:
            _atomic_write_json(self.snapshot_cache_path, snapshot)
        _atomic_write_json(self.state_cache_path, state_payload)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._poll_loop, name="display-agent-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            self._stop_event.wait(self.config.poll_interval_seconds)

    def _rewrite_local_asset_urls(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        resolved = deepcopy(snapshot)
        theme = resolved.get("theme") or {}
        for asset_key in ("background_asset", "logo_asset"):
            asset = theme.get(asset_key)
            if not asset:
                continue
            asset_id = str(asset["asset_id"])
            if self.get_asset_path(asset_id) is None:
                theme[asset_key] = None
                continue
            asset["content_url"] = f"/local/display/assets/{asset_id}?v={asset.get('checksum_sha256', '')}"
        return resolved

    def _download_asset(self, asset: dict[str, Any]) -> bool:
        asset_id = str(asset["asset_id"])
        source_url = asset.get("content_url")
        if not source_url:
            return False

        if source_url.startswith("/"):
            source_url = self.config.build_backend_url(source_url)

        checksum = asset.get("checksum_sha256", asset_id)
        suffix = Path(urlsplit(source_url).path).suffix or ".bin"
        target_name = f"{asset_id}-{checksum}{suffix}"
        target_path = self.assets_dir / target_name
        if target_path.exists():
            with self._lock:
                self.state.asset_files[asset_id] = target_name
            return True

        try:
            response = self.session.get(source_url, headers=self._backend_headers, timeout=10)
            response.raise_for_status()
            with target_path.open("wb") as output:
                output.write(response.content)
        except (OSError, requests.RequestException):
            LOGGER.warning("Failed to cache display asset asset_id=%s source_url=%s", asset_id, source_url, exc_info=True)
            with self._lock:
                self.state.asset_files.pop(asset_id, None)
            return False

        with self._lock:
            self.state.asset_files[asset_id] = target_name
        return True

    def poll_once(self) -> None:
        snapshot_url = self.config.build_backend_url(f"/api/display/taps/{self.config.tap_id}/snapshot")
        headers = dict(self._backend_headers)

        with self._lock:
            if self.state.etag:
                headers["If-None-Match"] = self.state.etag

        try:
            response = self.session.get(snapshot_url, headers=headers, timeout=10)
            polled_at = _utcnow().isoformat()
            if response.status_code == 304:
                with self._lock:
                    self.state.last_poll_at = polled_at
                    self.state.last_success_at = polled_at
                    self.state.consecutive_failures = 0
                self._persist_state()
                return

            response.raise_for_status()
            payload = response.json()
            for asset_key in ("background_asset", "logo_asset"):
                asset = ((payload.get("theme") or {}).get(asset_key))
                if asset:
                    self._download_asset(asset)

            resolved_snapshot = self._rewrite_local_asset_urls(payload)
            with self._lock:
                self.state.snapshot = resolved_snapshot
                self.state.etag = response.headers.get("ETag") or f'"{payload.get("content_version", "")}"'
                self.state.last_poll_at = polled_at
                self.state.last_success_at = polled_at
                self.state.consecutive_failures = 0
            self._persist_state()
        except requests.RequestException:
            LOGGER.exception("Snapshot poll failed")
            with self._lock:
                self.state.last_poll_at = _utcnow().isoformat()
                self.state.consecutive_failures += 1
            self._persist_state()

    def get_asset_path(self, asset_id: str) -> Path | None:
        with self._lock:
            filename = self.state.asset_files.get(str(asset_id))
        if not filename:
            return None
        candidate = self.assets_dir / filename
        if not candidate.exists():
            return None
        return candidate

    def is_backend_link_lost(self) -> bool:
        with self._lock:
            last_success_at = self.state.last_success_at
            consecutive_failures = self.state.consecutive_failures

        if consecutive_failures >= self.config.backend_lost_failures:
            return True

        parsed_success = _parse_iso_datetime(last_success_at)
        if parsed_success is None:
            return False
        elapsed = (_utcnow() - parsed_success).total_seconds()
        return elapsed > self.config.backend_lost_after_seconds

    def read_runtime_payload(self) -> dict[str, Any]:
        runtime: dict[str, Any]
        if self.config.runtime_path.exists():
            try:
                runtime = json.loads(self.config.runtime_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                runtime = {
                    "schema_version": 1,
                    "tap_id": self.config.tap_id,
                    "phase": "blocked",
                    "reason_code": "controller_runtime_stale",
                    "card_present": False,
                }
        else:
            runtime = {
                "schema_version": 1,
                "tap_id": self.config.tap_id,
                "phase": "idle",
                "reason_code": None,
                "card_present": False,
                "current_volume_ml": 0,
                "current_cost_cents": 0,
            }

        runtime_updated_at = _parse_iso_datetime(runtime.get("updated_at"))
        controller_runtime_stale = False
        if runtime_updated_at is not None:
            controller_runtime_stale = (
                (_utcnow() - runtime_updated_at).total_seconds() > self.config.runtime_stale_after_seconds
                and runtime.get("phase") not in {"idle", "blocked", "finished"}
            )

        return {
            "runtime": runtime,
            "health": {
                "backend_link_lost": self.is_backend_link_lost(),
                "last_backend_success_at": self.state.last_success_at,
                "last_backend_poll_at": self.state.last_poll_at,
                "consecutive_backend_failures": self.state.consecutive_failures,
                "controller_runtime_stale": controller_runtime_stale,
                "runtime_updated_at": runtime.get("updated_at"),
            },
        }

    def get_bootstrap_payload(self) -> dict[str, Any]:
        with self._lock:
            snapshot = deepcopy(self.state.snapshot)
            last_success_at = self.state.last_success_at
            last_poll_at = self.state.last_poll_at
            consecutive_failures = self.state.consecutive_failures

        return {
            "tap_id": self.config.tap_id,
            "snapshot": snapshot,
            "backend": {
                "link_lost": self.is_backend_link_lost(),
                "last_success_at": last_success_at,
                "last_poll_at": last_poll_at,
                "consecutive_failures": consecutive_failures,
                "has_cached_snapshot": snapshot is not None,
            },
        }
