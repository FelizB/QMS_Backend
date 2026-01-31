from typing import Optional

from app.application.interfaces.program_repository import IProgramRepository
from app.presentation.schemas.program_schema import ProgramOut


class ListProgramsUseCase:
    def __init__(self, repo: IProgramRepository) -> None:
        self.repo = repo

    async def execute(self, skip: int = 0, limit: int = 50, q: Optional[str] = None) -> list[
        ProgramOut]:
        rows = await self.repo.list_all(skip=skip, limit=limit, q=q)
        return [ProgramOut.model_validate(r, from_attributes=True) for r in rows]
