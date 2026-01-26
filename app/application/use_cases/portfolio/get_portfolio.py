from fastapi import HTTPException
from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioOut
from fastapi import HTTPException

from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioOut


class GetPortfolioUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, portfolio_id: int) -> PortfolioOut:
        obj = await self.repo.get(portfolio_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return PortfolioOut.model_validate(obj, from_attributes=True)
