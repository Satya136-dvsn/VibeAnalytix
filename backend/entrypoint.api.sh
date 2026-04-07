#!/bin/sh
set -eu

echo "[api-entrypoint] Running migrations..."
alembic upgrade head

echo "[api-entrypoint] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
