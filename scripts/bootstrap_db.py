import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

# Make project root importable
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.db import engine
from app.infrastructure.models.base import Base

# Import all models so they register on Base.metadata
from app.infrastructure.models import (
    user_model,
    project_model,
    portfolio_model,
    program_model,
    testcase_model,
    file_attachment_model,
    lookup_model,
    token_blacklist,
    tasks_model,
    activity_log,
    approval,
    role_matrix,
)


async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT to_regclass('public.users')"))
        exists = result.scalar()

        if not exists:
            print("No tables found. Creating schema...")
            await conn.run_sync(Base.metadata.create_all)
        else:
            print("Tables already exist. Skipping bootstrap.")


if __name__ == "__main__":
    asyncio.run(main())
