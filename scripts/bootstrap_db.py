from app.core.db import engine
from app.infrastructure.models.base import Base

# Import all model modules so they register on Base.metadata
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
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
