from typing import Optional

from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioPagedResult


class ListPortfoliosUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, skip: int = 0, limit: int = 50, q: Optional[str] = None) -> list[PortfolioPagedResult]:
        total, items = await self.repo.list(skip=skip, limit=limit, q=q)
        page = skip // limit + 1 if limit else 1

        return {"total": total, "items": items, "page": page, "page_size": limit}
