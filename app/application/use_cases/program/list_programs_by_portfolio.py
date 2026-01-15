from typing import Optional
from app.application.interfaces.program_repository import IProgramRepository
from app.presentation.schemas.program_schema import ProgramOut

class ListProgramsByPortfolioUseCase:
    def __init__(self, repo: IProgramRepository) -> None:
        self.repo = repo

    async def execute(self, portfolio_id: int, skip: int = 0, limit: int = 50, q: Optional[str] = None) -> list[ProgramOut]:
        rows = await self.repo.list_by_portfolio(portfolio_id, skip=skip, limit=limit, q=q)
        return [ProgramOut.model_validate(r, from_attributes=True) for r in rows]
