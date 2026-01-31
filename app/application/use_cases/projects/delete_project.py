from fastapi import HTTPException, status

from app.application.interfaces.project_repository import IProjectRepository
from app.presentation.schemas.project_schema import ProjectDeleteOut, ProjectSummaryDelete


class DeleteProjectUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute(self, project_id: int) -> bool | ProjectDeleteOut:
        details = await self.repo.soft_delete_and_return(project_id)

        if details is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        summary = ProjectSummaryDelete(
            project_id=details.project_id,
            name=details.name,
            updated_date=getattr(details, "updated_date", getattr(details, "deleted_at", None)),
            is_active=getattr(details, "is_active", True),
        )

        return ProjectDeleteOut(message="Project Deleted Successfully",
                                data=summary)
