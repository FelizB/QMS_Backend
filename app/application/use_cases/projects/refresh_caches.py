from typing import Optional

class RefreshProjectCachesUseCase:
    """
    Business operation to recalculate task/test progress for a project.
    This use case is framework-agnostic; async execution is orchestrated by presentation layer.
    """
    async def execute(self, project_id: int, release_id: Optional[int], run_async: bool) -> dict:
        # Plug in your domain-specific recalculation service here.
        # For now, return a stub payload describing the intent.
        return {
            "project_id": project_id,
            "release_id": release_id,
            "status": "queued" if run_async else "completed",
        }
