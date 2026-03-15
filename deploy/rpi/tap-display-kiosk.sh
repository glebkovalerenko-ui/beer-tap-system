#!/bin/sh
set -eu

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
DISPLAY_URL="${DISPLAY_URL:-http://127.0.0.1:18181/display/}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:18181/health}"
KIOSK_OUTPUT_NAME="${KIOSK_OUTPUT_NAME:-HDMI-A-1}"
KIOSK_OUTPUT_TRANSFORM="${KIOSK_OUTPUT_TRANSFORM:-90}"

resolve_browser() {
  if [ -n "${CHROMIUM_BIN:-}" ]; then
    printf '%s\n' "$CHROMIUM_BIN"
    return 0
  fi

  if command -v chromium >/dev/null 2>&1; then
    command -v chromium
    return 0
  fi

  if command -v chromium-browser >/dev/null 2>&1; then
    command -v chromium-browser
    return 0
  fi

  echo "Chromium binary not found" >&2
  exit 1
}

configure_output() {
  if ! command -v wlr-randr >/dev/null 2>&1; then
    return 0
  fi

  wlr-randr --output "$KIOSK_OUTPUT_NAME" --transform "$KIOSK_OUTPUT_TRANSFORM" >/dev/null 2>&1 || true
}

wait_for_agent() {
  python3 - "$HEALTH_URL" <<'PY'
import sys
import time
import urllib.request

url = sys.argv[1]

while True:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if 200 <= response.status < 500:
                sys.exit(0)
    except Exception:
        pass
    time.sleep(2)
PY
}

CHROMIUM_BIN="$(resolve_browser)"
WAYLAND_FLAGS=""
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
  WAYLAND_FLAGS="--enable-features=UseOzonePlatform --ozone-platform=wayland"
fi

configure_output
wait_for_agent

while true; do
  configure_output
  "$CHROMIUM_BIN" \
    $WAYLAND_FLAGS \
    --kiosk \
    --app="$DISPLAY_URL" \
    --no-first-run \
    --noerrdialogs \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --disable-features=Translate,MediaRouter \
    --check-for-update-interval=31536000 \
    --overscroll-history-navigation=0 \
    --disable-pinch \
    --incognito
  sleep 2
done
