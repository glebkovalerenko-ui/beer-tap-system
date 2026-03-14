import os
from pathlib import Path


DEFAULT_SERVER_URL = "http://cybeer-hub:8000"
DEFAULT_DEVICE_ENV_PATH = "/etc/beer-tap/device.env"
DEFAULT_DISPLAY_RUNTIME_PATH = "/run/beer-tap/display-runtime.json"


def normalize_server_url(value: str | None) -> str:
    normalized = (value or "").strip().rstrip("/")
    return normalized or DEFAULT_SERVER_URL


def normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized


def _load_device_env_file(path: str) -> dict[str, str]:
    env_values: dict[str, str] = {}
    candidate = Path(path)
    if not candidate.exists():
        return env_values

    for raw_line in candidate.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1].strip()
        env_values[key] = value
    return env_values


DEVICE_ENV_PATH = os.getenv("DEVICE_ENV_PATH", DEFAULT_DEVICE_ENV_PATH)
_DEVICE_ENV = _load_device_env_file(DEVICE_ENV_PATH)


def _get_setting(name: str, default: str) -> str:
    if name in os.environ and os.environ[name].strip():
        return os.environ[name].strip()
    return _DEVICE_ENV.get(name, default)


def _get_int_setting(name: str, default: int) -> int:
    raw_value = _get_setting(name, str(default))
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError):
        return default


SERVER_URL = normalize_server_url(_get_setting("SERVER_URL", DEFAULT_SERVER_URL))
TAP_ID = _get_int_setting("TAP_ID", 1)
PRICE_PER_100ML_CENTS = _get_int_setting("PRICE_PER_100ML_CENTS", 150)
SYNC_INTERVAL_SECONDS = _get_int_setting("SYNC_INTERVAL_SECONDS", 15)
PIN_RELAY = _get_int_setting("PIN_RELAY", 18)
PIN_FLOW_SENSOR = _get_int_setting("PIN_FLOW_SENSOR", 17)
FLOW_SENSOR_K_FACTOR = float(_get_setting("FLOW_SENSOR_K_FACTOR", "7.5"))
DISPLAY_RUNTIME_PATH = _get_setting("DISPLAY_RUNTIME_PATH", DEFAULT_DISPLAY_RUNTIME_PATH)

INTERNAL_TOKEN = normalize_token(
    _get_setting(
        "INTERNAL_TOKEN",
        _get_setting("INTERNAL_API_KEY", "demo-secret-key"),
    )
)
