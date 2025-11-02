#!/usr/bin/env sh
set -e

echo "[start.sh] normalizing line endings & starting…"

# --- wait for Postgres to be reachable (max ~30s) ---
echo "[start.sh] waiting for Postgres at ${DATABASE_URL}"
python - <<'PY'
import os, time
import sqlalchemy as sa

url=os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is not set")

engine=None
for i in range(30):
    try:
        engine=sa.create_engine(url, pool_pre_ping=True)
        with engine.connect() as _:
            pass
        print("[start.sh] Postgres is ready")
        break
    except Exception as e:
        print(f"[start.sh] waiting for DB… ({i+1}/30) {e}")
        time.sleep(1)
else:
    raise SystemExit("[start.sh] DB not reachable, giving up")
PY

# --- seed DB (idempotent; your seed.run() prints 'Vehicles already present.' if seeded) ---
echo "[start.sh] seeding DB…"
python - <<'PY'
try:
    from seed import run
    run()
    print("[start.sh] seed completed")
except Exception as e:
    # Do not crash the container if already seeded etc.
    print(f"[start.sh] seed warning: {e}")
PY

# --- launch API ---
echo "[start.sh] launching uvicorn…"
exec uvicorn app:app --host 0.0.0.0 --port 8000
