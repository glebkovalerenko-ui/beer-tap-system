#!/bin/sh
set -eu

TARGET_USER="${TARGET_USER:-cybeer}"
TARGET_GROUP="${TARGET_GROUP:-cybeer}"
TARGET_HOME="${TARGET_HOME:-/home/$TARGET_USER}"
REPO_ROOT="${REPO_ROOT:-$TARGET_HOME/beer-tap-system}"
RUNTIME_ROOT="${RUNTIME_ROOT:-$TARGET_HOME/.local/share/beer-tap}"
VENV_ROOT="${VENV_ROOT:-$RUNTIME_ROOT/venvs}"
CONTROLLER_VENV="$VENV_ROOT/controller"
DISPLAY_AGENT_VENV="$VENV_ROOT/display-agent"
CONTROLLER_REQUIREMENTS="$REPO_ROOT/rpi-controller/requirements.txt"
DISPLAY_AGENT_REQUIREMENTS="$REPO_ROOT/tap-display-agent/requirements.txt"

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  printf '[%s] %s\n' "$(timestamp_utc)" "$*"
}

fail() {
  printf '[%s] ERROR: %s\n' "$(timestamp_utc)" "$*" >&2
  exit 1
}

run_as_target() {
  if [ "$(id -un)" = "$TARGET_USER" ]; then
    sh -c "$1"
    return 0
  fi

  if [ "$(id -u)" -eq 0 ]; then
    sudo -H -u "$TARGET_USER" sh -c "$1"
    return 0
  fi

  fail "Run this script as $TARGET_USER or via sudo."
}

ensure_dir_contract() {
  path="$1"
  mode="$2"

  mkdir -p "$path"

  if [ "$(id -u)" -eq 0 ]; then
    chown "$TARGET_USER:$TARGET_GROUP" "$path"
  fi

  chmod "$mode" "$path"

  if [ ! -w "$path" ]; then
    fail "Path is not writable: $path. Re-run with sudo to repair ownership drift."
  fi
}

ensure_tree_owned() {
  path="$1"

  if [ ! -e "$path" ]; then
    return 0
  fi

  if [ "$(id -u)" -eq 0 ]; then
    chown -R "$TARGET_USER:$TARGET_GROUP" "$path"
    return 0
  fi

  if [ ! -w "$path" ]; then
    fail "Path is not writable: $path. Re-run with sudo to repair ownership drift."
  fi
}

venv_includes_system_site_packages() {
  venv_path="$1"
  expected="$2"
  config_path="$venv_path/pyvenv.cfg"

  [ -f "$config_path" ] || return 1
  grep -Eq "^include-system-site-packages = $expected$" "$config_path"
}

ensure_venv() {
  venv_path="$1"
  requirements_path="$2"
  include_system_site_packages="$3"
  label="$4"

  recreate=0

  ensure_tree_owned "$venv_path"

  if [ ! -x "$venv_path/bin/python" ]; then
    recreate=1
  fi

  if ! venv_includes_system_site_packages "$venv_path" "$include_system_site_packages"; then
    recreate=1
  fi

  if [ "$recreate" -eq 1 ]; then
    log "provisioning $label venv path=$venv_path recreate=yes system_site_packages=$include_system_site_packages"
    run_as_target "rm -rf '$venv_path'"
    if [ "$include_system_site_packages" = "true" ]; then
      run_as_target "python3 -m venv --system-site-packages '$venv_path'"
    else
      run_as_target "python3 -m venv '$venv_path'"
    fi
  else
    log "provisioning $label venv path=$venv_path recreate=no system_site_packages=$include_system_site_packages"
  fi

  ensure_tree_owned "$venv_path"
  run_as_target "'$venv_path/bin/python' -m pip install --disable-pip-version-check --upgrade --requirement '$requirements_path'"
  ensure_tree_owned "$venv_path"
}

main() {
  log "starting Pi runtime venv provisioning user=$(id -un) uid=$(id -u)"
  [ -f "$CONTROLLER_REQUIREMENTS" ] || fail "Missing controller requirements: $CONTROLLER_REQUIREMENTS"
  [ -f "$DISPLAY_AGENT_REQUIREMENTS" ] || fail "Missing display-agent requirements: $DISPLAY_AGENT_REQUIREMENTS"

  ensure_dir_contract "$RUNTIME_ROOT" 0755
  ensure_dir_contract "$VENV_ROOT" 0755

  ensure_venv "$CONTROLLER_VENV" "$CONTROLLER_REQUIREMENTS" true "controller"
  ensure_venv "$DISPLAY_AGENT_VENV" "$DISPLAY_AGENT_REQUIREMENTS" false "display-agent"

  log "Pi runtime venv provisioning completed runtime_root=$RUNTIME_ROOT venv_root=$VENV_ROOT"
}

main "$@"
