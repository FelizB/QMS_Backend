from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.settings import settings
from typing import AsyncGenerator

engine = create_async_engine(
    settings.db_url,
    echo=False,
    future=True,
    pool_pre_ping=False,
    pool_recycle=1800,
)

# Exported maker for both request-scoped sessions and "fresh-session" audits
AsyncSessionMaker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


# FastAPI dependency
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionMaker() as session:
        try:
            yield session
        finally:
            # Explicit close is optional; context manager handles it
            await session.close()
