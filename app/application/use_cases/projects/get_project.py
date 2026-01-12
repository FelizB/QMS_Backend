from app.application.interfaces.project_repository import IProjectRepository
from app.presentation.schemas.project_schema import ProjectOut, ProjectSummary

class GetProjectUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute_full(self, project_id: int) -> ProjectOut | None:
        obj = await self.repo.get_by_id(project_id)
        return None if not obj else ProjectOut.model_validate(obj, from_attributes=True)

    async def execute_summary(self, project_id: int) -> ProjectSummary | None:
        obj = await self.repo.get_by_id(project_id)
        return None if not obj else ProjectSummary.model_validate(obj, from_attributes=True)
