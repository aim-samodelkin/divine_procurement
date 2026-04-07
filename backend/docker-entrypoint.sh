#!/bin/sh
set -e
cd /app

echo "Running Alembic migrations..."
alembic upgrade head

if [ "${SERVICE:-}" = "app" ] && [ -n "${BOOTSTRAP_ADMIN_EMAIL:-}" ] && [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
  echo "Checking bootstrap admin (only if DB has no users)..."
  python scripts/bootstrap_admin.py || true
fi

exec "$@"
