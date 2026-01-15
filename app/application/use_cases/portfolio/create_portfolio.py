from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioCreate, PortfolioOut

class CreatePortfolioUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, payload: PortfolioCreate) -> PortfolioOut:
        data = payload.model_dump(exclude_unset=True)
        created = await self.repo.create(data)
        return PortfolioOut.model_validate(created, from_attributes=True)
