#!/usr/bin/env bash
set -euo pipefail

export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0

REPO_DIR=/home/cybeer/beer-tap-system
COMPOSE_FILE="$REPO_DIR/docker-compose.yml"
ENV_FILE="$REPO_DIR/.env"
SYNCTHING_CONFIG=/home/cybeer/.local/state/syncthing/config.xml
SYNCTHING_FOLDER_ID=beer-tap-system-dev
STATE_DIR=/var/lib/beer-tap-sync
LOCK_FILE=/run/beer-tap-sync-reconcile.lock
LAST_RUNTIME_FINGERPRINT_FILE="$STATE_DIR/last_backend_runtime_fingerprint"
LAST_BUILD_FINGERPRINT_FILE="$STATE_DIR/last_backend_build_fingerprint"
HEALTHCHECK_URL=http://127.0.0.1:8000/api/system/status
EXPECTED_BACKEND_BIND="$REPO_DIR/backend"

log() {
  printf '[beer-tap-sync] %s\n' "$*"
}

defer() {
  log "$1"
  exit 0
}

require_path() {
  local path="$1"
  [[ -e "$path" ]] || defer "required path missing: $path"
}

get_syncthing_api_key() {
  python3 - "$SYNCTHING_CONFIG" <<'PY'
import sys
import xml.etree.ElementTree as ET

config_path = sys.argv[1]
root = ET.parse(config_path).getroot()
gui = root.find("./gui")
if gui is None:
    raise SystemExit(1)
api_key = gui.findtext("apikey", "").strip()
if not api_key:
    raise SystemExit(1)
print(api_key)
PY
}

get_syncthing_status() {
  local api_key="$1"
  curl -fsS -H "X-API-Key: $api_key" "http://127.0.0.1:8384/rest/db/status?folder=$SYNCTHING_FOLDER_ID"
}

parse_status_field() {
  local json="$1"
  local field="$2"
  STATUS_JSON="$json" python3 - "$field" <<'PY'
import json
import os
import sys

field = sys.argv[1]
value = json.loads(os.environ["STATUS_JSON"]).get(field, "")
print(value)
PY
}

compute_runtime_fingerprint() {
  {
    sha256sum "$COMPOSE_FILE"
    sha256sum "$ENV_FILE"
    find "$REPO_DIR/backend" \
      \( -path "$REPO_DIR/backend/.pytest_cache" -o -path "$REPO_DIR/backend/.pytest_cache/*" \
         -o -path "$REPO_DIR/backend/__pycache__" -o -path "$REPO_DIR/backend/__pycache__/*" \
         -o -path "$REPO_DIR/backend/storage" -o -path "$REPO_DIR/backend/storage/*" \) -prune \
      -o -type f -print0 \
      | sort -z \
      | xargs -0 sha256sum
  } | sha256sum | awk '{print $1}'
}

compute_build_fingerprint() {
  {
    sha256sum "$COMPOSE_FILE"
    sha256sum "$ENV_FILE"
    sha256sum "$REPO_DIR/backend/Dockerfile"
    find "$REPO_DIR/backend" \
      \( -name 'requirements*.txt' -o -name 'entrypoint.sh' \) \
      -type f -print0 \
      | sort -z \
      | xargs -0 sha256sum
  } | sha256sum | awk '{print $1}'
}

backend_mount_source() {
  local inspect_json
  inspect_json="$(docker inspect beer_backend_api)"
  INSPECT_JSON="$inspect_json" python3 - <<'PY'
import json
import os

data = json.loads(os.environ["INSPECT_JSON"])
mounts = data[0].get("Mounts", [])
for mount in mounts:
    if mount.get("Destination") == "/app":
        print(mount.get("Source", ""))
        break
PY
}

wait_for_backend_health() {
  local attempt
  for attempt in $(seq 1 18); do
    if curl -fsS "$HEALTHCHECK_URL" >/dev/null; then
      return 0
    fi
    sleep 5
  done
  return 1
}

mkdir -p "$STATE_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  exit 0
fi

require_path "$REPO_DIR"
require_path "$COMPOSE_FILE"
require_path "$ENV_FILE"
require_path "$SYNCTHING_CONFIG"

api_key="$(get_syncthing_api_key)" || defer "unable to read Syncthing API key"
status_json="$(get_syncthing_status "$api_key")" || defer "Syncthing GUI is not ready yet"

state="$(parse_status_field "$status_json" state)"
need_total="$(parse_status_field "$status_json" needTotalItems)"
errors="$(parse_status_field "$status_json" errors)"
pull_errors="$(parse_status_field "$status_json" pullErrors)"
receive_only_total="$(parse_status_field "$status_json" receiveOnlyTotalItems)"
sequence="$(parse_status_field "$status_json" sequence)"

[[ "$state" == "idle" ]] || defer "Syncthing folder is not idle yet (state=$state)"
[[ "$need_total" == "0" ]] || defer "Syncthing still has pending items ($need_total)"
[[ "$errors" == "0" ]] || defer "Syncthing reports folder errors ($errors)"
[[ "$pull_errors" == "0" ]] || defer "Syncthing reports pull errors ($pull_errors)"
[[ "$receive_only_total" == "0" ]] || defer "Syncthing reports receive-only drift ($receive_only_total)"

current_runtime_fingerprint="$(compute_runtime_fingerprint)"
current_build_fingerprint="$(compute_build_fingerprint)"
last_runtime_fingerprint=""
last_build_fingerprint=""
if [[ -f "$LAST_RUNTIME_FINGERPRINT_FILE" ]]; then
  last_runtime_fingerprint="$(<"$LAST_RUNTIME_FINGERPRINT_FILE")"
fi
if [[ -f "$LAST_BUILD_FINGERPRINT_FILE" ]]; then
  last_build_fingerprint="$(<"$LAST_BUILD_FINGERPRINT_FILE")"
fi

if [[ "$current_runtime_fingerprint" == "$last_runtime_fingerprint" ]]; then
  exit 0
fi

compose_args=(up -d postgres beer_backend_api)
if [[ "$current_build_fingerprint" != "$last_build_fingerprint" ]]; then
  compose_args=(up -d --build postgres beer_backend_api)
  log "detected Docker build input changes"
fi

log "applying backend snapshot from $REPO_DIR (syncthing sequence=$sequence)"
/usr/bin/docker compose \
  --project-directory "$REPO_DIR" \
  -f "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" \
  "${compose_args[@]}"

mount_source="$(backend_mount_source)"
if [[ "$mount_source" != "$EXPECTED_BACKEND_BIND" ]]; then
  log "unexpected backend bind mount: $mount_source"
  exit 1
fi

if ! wait_for_backend_health; then
  log "backend healthcheck did not recover in time"
  exit 1
fi

printf '%s\n' "$current_runtime_fingerprint" >"$LAST_RUNTIME_FINGERPRINT_FILE"
printf '%s\n' "$current_build_fingerprint" >"$LAST_BUILD_FINGERPRINT_FILE"
log "backend snapshot applied successfully"
