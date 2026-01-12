from app.application.interfaces.project_repository import IProjectRepository

class DeleteProjectUseCase:
    def __init__(self, repo: IProjectRepository) -> None:
        self.repo = repo

    async def execute(self, project_id: int) -> bool:
        return await self.repo.soft_delete_and_return(project_id)
