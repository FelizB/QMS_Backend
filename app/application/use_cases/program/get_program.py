from fastapi import HTTPException
from app.application.interfaces.program_repository import IProgramRepository
from app.presentation.schemas.program_schema import ProgramOut

class GetProgramUseCase:
    def __init__(self, repo: IProgramRepository) -> None:
        self.repo = repo

    async def execute(self, program_id: int) -> ProgramOut:
        obj = await self.repo.get_by_id(program_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Program not found")
        return ProgramOut.model_validate(obj, from_attributes=True)
