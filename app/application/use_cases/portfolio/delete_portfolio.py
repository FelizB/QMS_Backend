from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioDeleteResponse, PortfolioOut


class DeletePortfolioUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, portfolio_id: int, concurrency_guid: str) -> PortfolioOut:
        deleted = await self.repo.soft_delete(portfolio_id, concurrency_guid)
        return PortfolioDeleteResponse(message="Portfolio deleted successfully",
                                       data=PortfolioOut.model_validate(deleted, from_attributes=True))
