set -euo pipefail

DB_SERVICE="${DB_SERVICE:-db}"
API_SERVICE="${API_SERVICE:-api}"
MIGRATIONS_SERVICE="${MIGRATIONS_SERVICE:-migrations}"
ALEMBIC_INI="${ALEMBIC_INI:-alembic.ini}"
VERSIONS_DIR="${VERSIONS_DIR:-migrations/versions}"
PGUSER="${PGUSER:-admin}"
PGDB="${PGDB:-qms}"
PGPORT_IN_CONTAINER="${PGPORT_IN_CONTAINER:-5432}"

log()  { printf "\033[36m» %s\033[0m\n" "$*"; }
ok()   { printf "\033[32m✔ %s\033[0m\n" "$*"; }
warn() { printf "\033[33m⚠ %s\033[0m\n" "$*"; }
err()  { printf "\033[31m✘ %s\033[0m\n" "$*"; }

alembic() {
  docker compose run --rm "$MIGRATIONS_SERVICE" -c "$ALEMBIC_INI" "$@"
}

wait_for_db() {
  log "Waiting for Postgres to be ready…"
  for i in {1..60}; do
    if docker compose exec -T "$DB_SERVICE" pg_isready -U "$PGUSER" -d "$PGDB" -h localhost -p "$PGPORT_IN_CONTAINER" >/dev/null 2>&1; then
      ok "Postgres is ready."
      return
    fi
    sleep 1
  done
  err "Postgres did not become ready in time."; exit 1
}

count_versions() {
  [[ -d "$VERSIONS_DIR" ]] || { echo 0; return; }
  find "$VERSIONS_DIR" -maxdepth 1 -type f -name "*.py" | wc -l | tr -d ' '
}

log "Starting DB service…"
docker compose up -d "$DB_SERVICE"
wait_for_db

mkdir -p "$VERSIONS_DIR"
PRE_COUNT="$(count_versions)"
log "Existing migration files: $PRE_COUNT"

if [[ "$PRE_COUNT" -gt 0 ]]; then
  # We already have migrations; ensure DB is at head BEFORE autogenerate
  log "Upgrading DB to current head (idempotent)…"
  alembic upgrade head
  ok "DB is at head."

  log "Autogenerating new migration (if changes exist)…"
  set +e
  OUT="$(alembic revision --autogenerate -m "auto: $(date -u +%Y-%m-%dT%H:%M:%SZ)")"
  RC=$?
  set -e
  echo "$OUT"

  if [[ $RC -ne 0 ]]; then
    err "Autogenerate failed."; exit $RC
  fi

  if echo "$OUT" | grep -qi "No changes detected"; then
    ok "No model changes detected."
  else
    ok "New migration created."
    log "Upgrading DB to new head…"
    alembic upgrade head
    ok "DB upgraded."
  fi
else
  # No migrations yet → create initial and upgrade
  log "No migration files found → creating initial autogenerate…"
  alembic revision --autogenerate -m "init: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  ok "Initial migration created."
  log "Upgrading DB to head…"
  alembic upgrade head
  ok "DB upgraded."
fi

# Verify pass – should produce "No changes detected"
log "Verifying schema state against models…"
set +e
VERIFY="$(alembic revision --autogenerate -m "verify: $(date -u +%Y-%m-%dT%H:%M:%SZ)")"
RC=$?
set -e
echo "$VERIFY"

if [[ $RC -ne 0 ]]; then
  err "Verification autogenerate failed."; exit $RC
fi

if echo "$VERIFY" | grep -qi "No changes detected"; then
  ok "Schema is in sync with models."
else
  err "Autogenerate still detected diffs *after* upgrade. Review your imports/env.py or model state."
  # remove spurious verify revision(s) to keep tree clean

fi

# Optional quick glance at tables
log "DB tables:"
docker compose exec -T "$DB_SERVICE" psql -U "$PGUSER" -d "$PGDB" -c '\dt' || true

# Start API
log "Starting API…"
docker compose up -d "$API_SERVICE"
ok "All done."
