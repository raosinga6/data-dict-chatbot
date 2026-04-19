#!/usr/bin/env bash
set -euo pipefail

cd backend

echo "==> Installing dependencies"
pip install -r requirements.txt -q

echo "==> DATABASE_URL=${DATABASE_URL}"   # shows which DB is active

echo "==> Running Alembic on test DB"
# Only run migrations if using a real DB — skip for SQLite in CI
if [[ "${DATABASE_URL}" != sqlite* ]]; then
  alembic upgrade head
fi

echo "==> Running pytest"
pytest tests/ -v --tb=short