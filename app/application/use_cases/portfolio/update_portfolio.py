from app.application.interfaces.portfolio_repository import IPortfolioRepository
from app.presentation.schemas.portfolio_schema import PortfolioUpdate, PortfolioOut


class UpdatePortfolioUseCase:
    def __init__(self, repo: IPortfolioRepository) -> None:
        self.repo = repo

    async def execute(self, portfolio_id: int, payload: PortfolioUpdate) -> PortfolioOut:
        data = payload.model_dump(exclude_unset=True)
        concurrency_guid = data.pop("concurrency_guid")
        try:
            updated = await self.repo.update(portfolio_id, data, concurrency_guid)
        except Exception as e:
            # your repo can raise HTTPException(409, ...) or IntegrityError mapped to HTTPException
            raise
        return PortfolioOut.model_validate(updated, from_attributes=True)
