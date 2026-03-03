#!/bin/sh
set -eu

python - <<'PY'
from startup_checks import redact_database_url
import os

print(f"[entrypoint] DATABASE_URL={redact_database_url(os.getenv('DATABASE_URL'))}")
PY

python -m alembic upgrade head

if [ "$#" -eq 0 ]; then
  set -- uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

exec "$@"
