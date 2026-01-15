from typing import Optional
from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioOut

class ListPortfoliosUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, skip: int = 0, limit: int = 50, q: Optional[str] = None) -> list[PortfolioOut]:
        rows = await self.repo.list(skip=skip, limit=limit, q=q)
        return [PortfolioOut.model_validate(r, from_attributes=True) for r in rows]
