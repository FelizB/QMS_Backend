
#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (edit as needed)
# ─────────────────────────────────────────────────────────────────────────────
VENV_PATH=".venv"
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="admin"
DB_PASS="admin123"
DB_NAME="qms"
SYNC_URL="postgresql+psycopg2://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
API_SERVICE="api"     # docker compose service name for API
DB_SERVICE="db"       # docker compose service name for Postgres
MIGRATIONS_INI="alembic.ini"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }

require_venv() {
  if [[ ! -d "${VENV_PATH}" ]]; then
    red "venv not found at ${VENV_PATH}. Create it with: python3 -m venv .venv"
    exit 1
  fi
  # shellcheck disable=SC1090
  source "${VENV_PATH}/bin/activate"
}

confirm() {
  read -r -p "$1 [y/N] " ans
  [[ "${ans}" == "y" || "${ans}" == "Y" ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
yellow ">> Host-side dev migration started"

require_venv
export MIGRATIONS_DB_URL="${SYNC_URL}"

green "1) Starting DB (Compose)…"
docker compose up -d "${DB_SERVICE}"

green "2) (Optional) Reset DB data volume"
if confirm "Do you want to DROP ALL DATA by recreating the Docker volume?"; then
  docker compose down -v
  docker compose up -d "${DB_SERVICE}"
  green "DB volume recreated."
fi

green "3) Ensure Alembic sees all models (env.py must import your model modules)"
# Example reminder (no-op):
echo "   - Check migrations/env.py imports: app.infrastructure.models.user_model, project_model, etc."

green "4) Clean previous failed/empty migration (optional)"
if confirm "Remove all migration scripts under migrations/versions/?"; then
  rm -rf migrations/versions/*
  mkdir -p migrations/versions
  yellow "   versions cleared."
fi

green "5) Stamp base (optional, only if DB is out-of-sync)"
if confirm "Stamp DB to base (forget previous revision pointers)?"; then
  python -m alembic -c "${MIGRATIONS_INI}" stamp base
fi

green "6) Autogenerate migration"
python -m alembic -c "${MIGRATIONS_INI}" revision --autogenerate -m "dev: autogenerate"

green "7) Apply migration → upgrade head"
python -m alembic -c "${MIGRATIONS_INI}" upgrade head

green "8) Verify tables (projects/users, etc.)"
docker compose exec "${DB_SERVICE}" psql -U "${DB_USER}" -d "${DB_NAME}" -c '\dt' || true
docker compose exec "${DB_SERVICE}" psql -U "${DB_USER}" -d "${DB_NAME}" -c '\d+ users' || true
docker compose exec "${DB_SERVICE}" psql -U "${DB_USER}" -d "${DB_NAME}" -c '\d+ projects' || true

green "9) Start API in foreground (hot-reload if configured)"
docker compose up "${API_SERVICE}"

green "✅ Done (host-side)."

