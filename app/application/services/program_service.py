
# application/services/program_service.py
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.infrastructure.models.program_model import Program
from app.application.interfaces.program_repository import IProgramRepository

class ProgramService:
    def __init__(self, repo: IProgramRepository, session: AsyncSession):
        self.repo = repo
        self.session = session

    async def create(self, data: dict) -> Program:
        # If is_default => unset others in same portfolio (or rely on conflict and retry)
        if data.get("is_default"):
            await self.session.execute(
                update(Program)
                .where(Program.portfolio_id == data["portfolio_id"])
                .where(Program.is_default.is_(True))
                .values(is_default=False)
            )
        return await self.repo.create(data)

    async def update(self, program_id: int, data: dict, concurrency_guid: str) -> Program:
        # Same default logic on updates
        if data.get("is_default"):
            # Need the target to know portfolio (could be changing)
            # First fetch the current one to get portfolio_id if not provided
            # (Minimal extra query for correctness)
            current = await self.repo.get(program_id)
            if not current:
                raise HTTPException(status_code=404, detail="Program not found")
            target_portfolio_id = data.get("portfolio_id", current.portfolio_id)
            await self.session.execute(
                update(Program)
                .where(Program.portfolio_id == target_portfolio_id)
                .where(Program.is_default.is_(True))
                .where(Program.id != program_id)
                .values(is_default=False)
            )
        return await self.repo.update(program_id, data, concurrency_guid)

    async def soft_delete(self, program_id: int, concurrency_guid: str) -> Program:
        return await self.repo.soft_delete(program_id, concurrency_guid)
