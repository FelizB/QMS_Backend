# app/infrastructure/repositories/token_blacklist_repository.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, delete, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.token_blacklist import TokenBlacklist


def _is_postgres(session: AsyncSession) -> bool:
    try:
        name = session.bind.dialect.name  # type: ignore[attr-defined]
        return str(name).lower() == "postgresql"
    except Exception:
        return False


class TokenBlacklistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, *, user_id: int, jti: str, token_type: str, expires_at: datetime):
        """
        Insert a blacklist record. If a row with the same JTI already exists:
          - On Postgres: do nothing via ON CONFLICT (index on jti required).
          - On other DBs: ignore duplicate via IntegrityError trap.
        Caller is responsible for session.commit().
        """
        if _is_postgres(self.session):
            # Use Postgres dialect insert for ON CONFLICT DO NOTHING
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(TokenBlacklist).values(
                user_id=user_id, jti=jti, token_type=token_type, expires_at=expires_at
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=[TokenBlacklist.jti])
            await self.session.execute(stmt)
            return

        # Generic/portable path (SQLite/MySQL etc.)
        try:
            stmt = insert(TokenBlacklist).values(
                user_id=user_id, jti=jti, token_type=token_type, expires_at=expires_at
            )
            await self.session.execute(stmt)
        except IntegrityError:
            # Duplicate JTI (or other uniqueness hit) – ignore for idempotency
            # Let caller decide committing
            pass

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
