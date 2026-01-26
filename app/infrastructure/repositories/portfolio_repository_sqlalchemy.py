from typing import Tuple, List, Optional

from fastapi import HTTPException
from sqlalchemy import update, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.portfolio_model import Portfolio

MAX_LIMIT = 200


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

    async def list(self, skip: int = 0, limit: int = 50, q: Optional[str] = None) -> Tuple[int, List[Portfolio]]:
        # Guardrails
        if limit <= 0:
            limit = 50
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        if skip < 0:
            skip = 0

        base = (
            select(Portfolio)
            .where(Portfolio.is_deleted.is_(False)).limit(limit).offset(skip)
        )
        if q:
            base = base.where(Portfolio.name.ilike(f"%{q}%"))

        count_stmt = select(func.count()).select_from(base.subquery())
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar() or 0)

        # Page window: ORDER → OFFSET → LIMIT
        stmt = (
            base
            .order_by(Portfolio.id.desc())
            .offset(skip)
            .limit(limit)
        )

        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        # Return both total and items (better for clients)
        return total, items

    async def update(self, portfolio_id: int, data: dict, concurrency_guid: str) -> Portfolio:
        # optimistic concurrency
        stmt = (
            update(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .where(Portfolio.concurrency_guid == concurrency_guid)
            .where(Portfolio.is_deleted.is_(False))
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
            .where(Portfolio.is_deleted.is_(False))
            .values(is_deleted=True)
            .values(is_active=False)
            .returning(Portfolio)
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=409, detail="Concurrency conflict or portfolio not found")

        return obj
