import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ─────────────────────────────────────────────────────────────────────────────
# Ensure project root on sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

load_dotenv()

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# ─────────────────────────────────────────────────────────────────────────────
# Pick a SYNC DB URL for Alembic
db_url = (
        os.getenv("MIGRATIONS_DB_URL")
        or os.getenv("DATABASE_URL_SYNC")
        or os.getenv("DB_URL")
        or os.getenv("DATABASE_URL")
)

# Convert async URL to sync before setting into config
if db_url and db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("+asyncpg", "")

if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# ─────────────────────────────────────────────────────────────────────────────
# Import Base and ensure ALL model modules are imported so metadata is complete
from app.infrastructure.models.base import Base
# Import each model module so tables register on Base.metadata
from app.infrastructure.models import user_model, project_model, portfolio_model, program_model  # noqa: F401

target_metadata = Base.metadata

# ─────────────────────────────────────────────────────────────────────────────
# Keep False unless you truly use multiple schemas
INCLUDE_SCHEMAS = False


# VERSION_TABLE_SCHEMA = "qms"  # enable if you keep alembic_version in a custom schema

def include_object(obj, name, type_, reflected, compare_to):
    """
    Skip objects that explicitly opt out via info={"alembic_autogenerate": False},
    and skip known partial indexes by name (Postgres partial unique indexes).
    """
    try:
        if getattr(obj, "info", None) and obj.info.get("alembic_autogenerate") is False:
            return False
    except Exception:
        pass

    if type_ == "index" and name in {
        "uq_portfolio_default_singleton",
        "uq_program_default_per_portfolio",
    }:
        return False

    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        include_schemas=INCLUDE_SCHEMAS,
        include_object=include_object,
        # version_table_schema=VERSION_TABLE_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=INCLUDE_SCHEMAS,
            include_object=include_object,
            # version_table_schema=VERSION_TABLE_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
