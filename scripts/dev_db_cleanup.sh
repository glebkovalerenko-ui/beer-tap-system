#!/usr/bin/env bash
set -euo pipefail

docker exec beer_backend_api python /app/dev_db_cleanup.py "$@"
