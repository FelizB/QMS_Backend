from app.application.interfaces.program_repository import IProgramRepository
from app.presentation.schemas.program_schema import ProgramCreate, ProgramOut
from app.application.services.program_rules import ProgramRulesService

class CreateProgramUseCase:
    def __init__(self, repo: IProgramRepository, rules: ProgramRulesService) -> None:
        self.repo = repo
        self.rules = rules

    async def execute(self, payload: ProgramCreate) -> ProgramOut:
        data = payload.model_dump(exclude_unset=True)
        if data.get("is_default"):
            await self.rules.ensure_single_default_in_portfolio(data["portfolio_id"])
        created                                  = await self.repo.create(data)
        return ProgramOut.model_validate(created, from_attributes               = True)
