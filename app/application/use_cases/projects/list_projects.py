from app.application.interfaces.project_repository import IProjectRepository
from app.presentation.schemas.project_schema import ProjectSummary

class ListProjectsUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute(self, limit: int = 50, offset: int = 0) -> list[ProjectSummary]:
        rows = await self.repo.list(limit=limit, offset=offset)
        return [ProjectSummary.model_validate(r, from_attributes=True) for r in rows]
