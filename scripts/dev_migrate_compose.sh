
#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (edit as needed)
# ─────────────────────────────────────────────────────────────────────────────
DB_SERVICE="db"
API_SERVICE="api"
MIGRATIONS_SERVICE="migrations"
MIGRATIONS_INI="alembic.ini"
# Compose-side URL must resolve to service name 'db'
# Ensure .env has MIGRATIONS_DB_URL=postgresql+psycopg2://admin:admin123@db:5432/qms
# Ensure api uses APP_DB_URL=postgresql+asyncpg://admin:admin123@db:5432/qms

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }

confirm() {
  read -r -p "$1 [y/N] " ans
  [[ "${ans}" == "y" || "${ans}" == "Y" ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
yellow ">> Compose-side dev migration started"

green "1) Ensure migrations service bind-mounts the repo (docker-compose.yml):"
echo "   migrations:
      volumes:
        - .:/app
      entrypoint: [\"alembic\"]
      environment:
        DB_URL: \${MIGRATIONS_DB_URL}"

green "2) Start DB"
docker compose up -d "${DB_SERVICE}"

green "3) (Optional) Reset DB data volume"
if confirm "Do you want to DROP ALL DATA by recreating volume?"; then
  docker compose down -v
  docker compose up -d "${DB_SERVICE}"
  yellow "   DB volume recreated."
fi

green "4) Ensure env.py imports ALL models"
echo "   - In migrations/env.py: import your model modules so Base.metadata has all tables."

green "5) Clean previous failed/empty migration (optional)"
if confirm "Remove migration scripts under migrations/versions/?"; then
  rm -rf migrations/versions/*
  mkdir -p migrations/versions
  yellow "   versions cleared."
fi

green "6) Stamp base (optional)"
if confirm "Stamp DB to base (forget previous revision pointers)?"; then
  docker compose run --rm "${MIGRATIONS_SERVICE}" -c "${MIGRATIONS_INI}" stamp base
fi

green "7) Autogenerate migration (migrations ENTRYPOINT is already 'alembic')"
docker compose run --rm "${MIGRATIONS_SERVICE}" -c "${MIGRATIONS_INI}" revision --autogenerate -m "dev: autogenerate"

green "8) Apply migration → upgrade head"
docker compose run --rm "${MIGRATIONS_SERVICE}" -c "${MIGRATIONS_INI}" upgrade head

green "9) Verify tables"
docker compose exec "${DB_SERVICE}" psql -U admin -d qms -c '\dt' || true
docker compose exec "${DB_SERVICE}" psql -U admin -d qms -c '\d+ users' || true
docker compose exec "${DB_SERVICE}" psql -U admin -d qms -c '\d+ projects' || true

green "10) Start API (foreground)"
docker compose up "${API_SERVICE}"

green "✅ Done (Compose-side)."

