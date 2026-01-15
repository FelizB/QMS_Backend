from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.infrastructure.models.program_model import Program

class ProgramRulesService:
    """Cross-entity rules that require DB access but are business logic."""
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_single_default_in_portfolio(self, portfolio_id: int, skip_program_id: int | None = None) -> None:
        stmt = (
            update(Program)
            .where(Program.portfolio_id == portfolio_id)
            .where(Program.is_default.is_(True))
        )
        if skip_program_id:
            stmt = stmt.where(Program.id != skip_program_id)
        await self.session.execute(stmt.values(is_default=False))
