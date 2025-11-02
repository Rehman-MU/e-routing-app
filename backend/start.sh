#!/usr/bin/env sh
set -e

# seed tables + demo vehicles (id 1..5)
python - <<'PY'
from seed import run
run()
PY

# start the API
exec uvicorn app:app --host 0.0.0.0 --port 8000
