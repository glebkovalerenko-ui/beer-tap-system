#!/bin/sh
set -eu

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  printf '[%s] %s\n' "$(timestamp_utc)" "$*"
}

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-wayland}"
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
    log "wlr-randr not available; skipping output transform"
    return 0
  fi

  if wlr-randr --output "$KIOSK_OUTPUT_NAME" --transform "$KIOSK_OUTPUT_TRANSFORM" >/dev/null 2>&1; then
    log "applied output transform output=$KIOSK_OUTPUT_NAME transform=$KIOSK_OUTPUT_TRANSFORM"
    return 0
  fi

  log "failed to apply output transform output=$KIOSK_OUTPUT_NAME transform=$KIOSK_OUTPUT_TRANSFORM"
  return 0
}

wait_for_agent() {
  log "waiting for display agent health_url=$HEALTH_URL"
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
  log "display agent is reachable"
}

CHROMIUM_BIN="$(resolve_browser)"
log "starting tap display kiosk user=$(id -un) uid=$(id -u) display=${DISPLAY:-} wayland=$WAYLAND_DISPLAY session_type=$XDG_SESSION_TYPE runtime_dir=$XDG_RUNTIME_DIR"
log "resolved browser=$CHROMIUM_BIN display_url=$DISPLAY_URL health_url=$HEALTH_URL output=$KIOSK_OUTPUT_NAME transform=$KIOSK_OUTPUT_TRANSFORM"

configure_output
wait_for_agent

while true; do
  configure_output
  log "launching chromium in kiosk mode"
  if "$CHROMIUM_BIN" \
    --enable-features=UseOzonePlatform \
    --ozone-platform=wayland \
    --disable-gpu \
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
  then
    exit_code=0
  else
    exit_code=$?
  fi
  log "chromium exited exit_code=$exit_code; restarting in 2 seconds"
  sleep 2
done
