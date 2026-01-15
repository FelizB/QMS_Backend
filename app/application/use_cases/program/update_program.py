from app.application.interfaces.program_repository import IProgramRepository
from app.application.services.program_rules import ProgramRulesService
from app.presentation.schemas.program_schema import ProgramUpdate, ProgramOut

class UpdateProgramUseCase:
    def __init__(self, repo: IProgramRepository, rules: ProgramRulesService) -> None:
        self.repo = repo
        self.rules = rules

    async def execute(self, program_id: int, payload: ProgramUpdate) -> ProgramOut:
        data = payload.model_dump(exclude_unset=True)
        concurrency_guid = data.pop("concurrency_guid")
        # Enforce default uniqueness if toggling on (and consider portfolio_id changes)
        if data.get("is_default"):
            # Need target portfolio_id (either new or current)
            # Simpler approach: prefetch current to know portfolio_id if not provided
            current = await self.repo.get_by_id(program_id)
            target_portfolio_id = data.get("portfolio_id") or (current.portfolio_id if current else None)
            if target_portfolio_id:
                await self.rules.ensure_single_default_in_portfolio(target_portfolio_id, skip_program_id=program_id)

        updated = await self.repo.update_with_concurrency(program_id, data, concurrency_guid)
        return ProgramOut.model_validate(updated, from_attributes=True)
