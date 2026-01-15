from app.application.interfaces.program_repository import IProgramRepository
from app.presentation.schemas.program_schema import ProgramOut

class DeleteProgramUseCase:
    def __init__(self, repo: IProgramRepository) -> None:
        self.repo = repo

    async def execute(self                      , program_id                                              : int              , concurrency_guid: str) -> ProgramOut:
        deleted                                  = await self.repo.soft_delete_with_concurrency(program_id, concurrency_guid)
        return ProgramOut.model_validate(deleted, from_attributes                                          = True)