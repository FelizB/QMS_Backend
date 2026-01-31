from app.application.interfaces.project_repository import IProjectRepository
from app.presentation.schemas.project_schema import ProjectCreate, ProjectOut


class CreateProjectUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute(self, payload: ProjectCreate) -> ProjectOut:
        data = payload.model_dump(exclude_unset=True)
        created = await self.repo.create(data)
        return ProjectOut.model_validate(created, from_attributes=True)
