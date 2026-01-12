
from app.application.interfaces.project_repository import IProjectRepository
from app.presentation.schemas.project_schema import ProjectUpdate, ProjectOut

class UpdateProjectUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute(self, project_id: int, payload: ProjectUpdate) -> ProjectOut | None:
        fields = payload.model_dump(exclude_unset=True)
        updated = await self.repo.update_partial(project_id, fields)
        if not updated:
            return None
        return ProjectOut.model_validate(updated, from_attributes=True)
