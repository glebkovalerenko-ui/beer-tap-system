import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin


DEFAULT_DEVICE_ENV_PATH = "/etc/beer-tap/device.env"
DEFAULT_RUNTIME_PATH = "/run/beer-tap/display-runtime.json"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "cache"
DEFAULT_CLIENT_DIST_DIR = Path(__file__).resolve().parent.parent / "tap-display-client" / "dist"
PLACEHOLDER_PREFIXES = ("replace-with", "change-me")


def _load_device_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    candidate = Path(path)
    if not candidate.exists():
        return values

    for raw_line in candidate.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1].strip()
        values[key] = value
    return values


def _normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized


def _looks_like_placeholder(value: str | None) -> bool:
    normalized = _normalize_token(value).lower()
    if not normalized:
        return True
    return any(normalized.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


@dataclass(slots=True)
class AgentConfig:
    tap_id: int
    backend_url: str
    display_token: str
    runtime_path: Path
    cache_dir: Path
    client_dist_dir: Path
    poll_interval_seconds: int
    backend_lost_after_seconds: int
    backend_lost_failures: int
    runtime_stale_after_seconds: int
    host: str
    port: int

    @classmethod
    def load(cls) -> "AgentConfig":
        device_env_path = os.getenv("DEVICE_ENV_PATH", DEFAULT_DEVICE_ENV_PATH)
        device_env = _load_device_env_file(device_env_path)

        def get_value(name: str, default: str) -> str:
            if name in os.environ and os.environ[name].strip():
                return os.environ[name].strip()
            return device_env.get(name, default)

        display_token = _normalize_token(get_value("DISPLAY_API_KEY", ""))
        if _looks_like_placeholder(display_token):
            raise ValueError("DISPLAY_API_KEY must be configured for tap-display-agent.")

        return cls(
            tap_id=int(get_value("TAP_ID", "1")),
            backend_url=get_value("SERVER_URL", "http://127.0.0.1:8000").rstrip("/"),
            display_token=display_token,
            runtime_path=Path(get_value("DISPLAY_RUNTIME_PATH", DEFAULT_RUNTIME_PATH)),
            cache_dir=Path(get_value("DISPLAY_AGENT_CACHE_DIR", str(DEFAULT_CACHE_DIR))),
            client_dist_dir=Path(get_value("DISPLAY_CLIENT_DIST_DIR", str(DEFAULT_CLIENT_DIST_DIR))),
            poll_interval_seconds=int(get_value("DISPLAY_AGENT_POLL_INTERVAL_SECONDS", "5")),
            backend_lost_after_seconds=int(get_value("DISPLAY_AGENT_BACKEND_LOST_AFTER_SECONDS", "15")),
            backend_lost_failures=int(get_value("DISPLAY_AGENT_BACKEND_LOST_FAILURES", "2")),
            runtime_stale_after_seconds=int(get_value("DISPLAY_AGENT_RUNTIME_STALE_AFTER_SECONDS", "3")),
            host=get_value("DISPLAY_AGENT_HOST", "127.0.0.1"),
            port=int(get_value("DISPLAY_AGENT_PORT", "18181")),
        )

    def build_backend_url(self, path: str) -> str:
        return urljoin(f"{self.backend_url}/", path.lstrip("/"))
