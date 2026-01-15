from typing import Sequence, Optional
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.infrastructure.models.program_model import Program
from app.infrastructure.models.portfolio_model import Portfolio

class ProgramRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Program:
        # ensure portfolio exists
        portfolio_id = data["portfolio_id"]
        p = await self.session.get(Portfolio, portfolio_id)
        if not p:
            raise HTTPException(status_code=400, detail="Portfolio does not exist")

        obj = Program(**data)
        self.session.add(obj)
        try:
            await self.session.flush()
        except IntegrityError as e:
            raise HTTPException(status_code=409, detail="Program constraint violation") from e
        return obj

    async def get(self, program_id: int) -> Optional[Program]:
        res = await self.session.execute(select(Program).where(Program.id == program_id))
        return res.scalar_one_or_none()

    async def list_by_portfolio(self, portfolio_id: int, skip: int = 0, limit: int = 50, q: str | None = None) -> Sequence[Program]:
        stmt = select(Program).where(Program.portfolio_id == portfolio_id).offset(skip).limit(limit)
        if q:
            stmt = stmt.where(Program.name.ilike(f"%{q}%"))
        res = await self.session.execute(stmt.order_by(Program.id.desc()))
        return res.scalars().all()

    async def update(self, program_id: int, data: dict, concurrency_guid: str) -> Program:
        # If portfolio_id is changing, validate it exists
        if "portfolio_id" in data and data["portfolio_id"] is not None:
            p = await self.session.get(Portfolio, data["portfolio_id"])
            if not p:
                raise HTTPException(status_code=400, detail="New portfolio does not exist")

        stmt = (
            update(Program)
            .where(Program.id == program_id)
            .where(Program.concurrency_guid == concurrency_guid)
            .values(**data)
            .returning(Program)
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=409, detail="Concurrency conflict or program not found")
        return obj

    async def soft_delete(self, program_id: int, concurrency_guid: str) -> Program:
        stmt = (
            update(Program)
            .where(Program.id == program_id)
            .where(Program.concurrency_guid == concurrency_guid)
            .values(is_active=False)
            .returning(Program)
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=409, detail="Concurrency conflict or program not found")
        return obj
