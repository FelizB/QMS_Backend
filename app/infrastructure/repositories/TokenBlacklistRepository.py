# app/infrastructure/repositories/token_blacklist_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete
from app.infrastructure.models.token_blacklist import TokenBlacklist
from datetime import datetime, timezone


class TokenBlacklistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, *, user_id: int, jti: str, token_type: str, expires_at: datetime):
        stmt = insert(TokenBlacklist).values(
            user_id=user_id, jti=jti, token_type=token_type, expires_at=expires_at
        )
        # Postgres-only:
        stmt = stmt.on_conflict_do_nothing(index_elements=["jti"])
        await self.session.execute(stmt)

    async def is_blacklisted(self, jti: str) -> bool:
        res = await self.session.execute(
            select(TokenBlacklist.id).where(TokenBlacklist.jti == jti)
        )
        return res.scalar_one_or_none() is not None

    async def remove_by_jti(self, jti: str):
        await self.session.execute(delete(TokenBlacklist).where(TokenBlacklist.jti == jti))

    async def purge_expired(self):
        now = datetime.now(timezone.utc)
        await self.session.execute(
            delete(TokenBlacklist).where(TokenBlacklist.expires_at <= now)
        )
