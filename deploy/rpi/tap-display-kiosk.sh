#!/bin/sh
set -eu

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
DISPLAY_URL="http://127.0.0.1:18181/display/"
HEALTH_URL="http://127.0.0.1:18181/health"

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

wait_for_agent

while true; do
  chromium-browser \
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
