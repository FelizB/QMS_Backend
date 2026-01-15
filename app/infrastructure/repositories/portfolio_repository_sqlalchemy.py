from typing import Sequence, Optional
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.infrastructure.models.portfolio_model import Portfolio

class PortfolioRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Portfolio:
        obj = Portfolio(**data)
        self.session.add(obj)
        try:
            await self.session.flush()  # get PK
        except IntegrityError as e:
            raise HTTPException(status_code=409, detail="Portfolio constraint violation") from e
        return obj

    async def get(self, portfolio_id: int) -> Optional[Portfolio]:
        res = await self.session.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
        return res.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 50, q: str | None = None) -> Sequence[Portfolio]:
        stmt = select(Portfolio).offset(skip).limit(limit)
        if q:
            stmt = stmt.where(Portfolio.name.ilike(f"%{q}%"))
        res = await self.session.execute(stmt.order_by(Portfolio.id.desc()))
        return res.scalars().all()

    async def update(self, portfolio_id: int, data: dict, concurrency_guid: str) -> Portfolio:
        # optimistic concurrency
        stmt = (
            update(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .where(Portfolio.concurrency_guid == concurrency_guid)
            .values(**data)
            .returning(Portfolio)
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=409, detail="Concurrency conflict or portfolio not found")
        return obj

    async def soft_delete(self, portfolio_id: int, concurrency_guid: str) -> Portfolio:
        stmt = (
            update(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .where(Portfolio.concurrency_guid == concurrency_guid)
            .values(is_active=False)
            .returning(Portfolio)
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=409, detail="Concurrency conflict or portfolio not found")
        return obj
