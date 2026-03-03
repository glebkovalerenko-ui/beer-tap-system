# config.py

import os

DEFAULT_SERVER_URL = "http://cybeer-hub:8000"


def normalize_server_url(value: str | None) -> str:
    normalized = (value or "").strip().rstrip("/")
    return normalized or DEFAULT_SERVER_URL


SERVER_URL = normalize_server_url(os.getenv("SERVER_URL"))

TAP_ID = 1
PRICE_PER_100ML_CENTS = 150
SYNC_INTERVAL_SECONDS = 15
PIN_RELAY = 18
PIN_FLOW_SENSOR = 17
FLOW_SENSOR_K_FACTOR = 7.5


def normalize_token(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized


INTERNAL_TOKEN = normalize_token(
    os.getenv("INTERNAL_TOKEN") or os.getenv("INTERNAL_API_KEY") or "demo-secret-key"
)
