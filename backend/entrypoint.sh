#!/bin/bash
set -euo pipefail

echo "🔧 Environment:"
echo "  DB_HOST=${DB_HOST:-unset}"
echo "  DB_PORT=${DB_PORT:-unset}"
echo "  DB_NAME=${DB_NAME:-unset}"
echo "  APP_ENV=${APP_ENV:-development}"

# Wait for Postgres to be ready
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
  echo "⏳ Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
  sleep 2
done
echo "✅ Postgres is ready."

# Generate migration if none exists
if [ -z "$(ls -A alembic/versions)" ]; then
  echo "📦 Generating initial migration..."
  alembic revision --autogenerate -m "initial tables"
elif [ "${APP_ENV}" = "development" ]; then
  # In dev mode, always autogenerate a new migration
  echo "📦 Autogenerating migration for current models..."
  alembic revision --autogenerate -m "auto migration at startup" || true
fi

# Show current Alembic state
echo "🔎 Alembic current revision:"
alembic current --verbose || true

# Run migrations only if not at head
if ! alembic current --verbose | grep -q 'head'; then
  echo "🚀 Applying Alembic migrations to head..."
  echo "📜 SQL preview of migrations:"
  alembic upgrade head --sql
  alembic upgrade head
else
  echo "✅ Database already at head revision. Skipping migrations."
fi

# Start Uvicorn
echo "🚀 Starting Uvicorn..."
exec uvicorn backend_app.main:app --host 0.0.0.0 --port 8000 --reload