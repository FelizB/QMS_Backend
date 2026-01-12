
from typing import Optional
from app.application.interfaces.project_repository import IProjectRepository
from app.presentation.schemas.project_schema import ProjectCreate, ProjectOut

class CreateProjectUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute(self, payload: ProjectCreate, existing_project_id: Optional[int] = None) -> ProjectOut:
        data = payload.model_dump(exclude_unset=True)
        if existing_project_id is not None:
            src = await self.repo.get_by_id(existing_project_id)
            if src:
                src_dct = ProjectOut.model_validate(src, from_attributes=True).model_dump()
                for k, v in src_dct.items():
                    data.setdefault(k, v)
        created = await self.repo.create(data)
        return ProjectOut.model_validate(created, from_attributes=True)
