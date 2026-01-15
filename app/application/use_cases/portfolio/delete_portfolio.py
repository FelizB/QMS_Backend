from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioOut

class DeletePortfolioUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, portfolio_id: int, concurrency_guid: str) -> PortfolioOut:
        deleted = await self.repo.soft_delete_with_concurrency(portfolio_id, concurrency_guid)
        return PortfolioOut.model_validate(deleted, from_attributes=True)
