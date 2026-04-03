#!/bin/sh
set -e
cd /app
alembic upgrade head
python -m scripts.seed || true
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
