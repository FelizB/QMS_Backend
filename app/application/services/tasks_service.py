from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories.tasks_repository_sqlalchemy import TaskRepository
from app.domain.enum import TaskPriority, TaskStatus, TaskType
from app.presentation.schemas.tasks_schema import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, db: AsyncSession):
        self.repo = TaskRepository(db)

    async def list_task(self, project_id: int, params: dict):
        page = max(1, int(params.get("page", 1)))
        page_size = max(1, min(100, int(params.get("pageSize", params.get("page_size", 10)))))

        rows, total = await self.repo.list_paged(
            project_id=project_id,
            page=page,
            page_size=page_size,
            search=params.get("search"),
            type_=params.get("type"),
            priority=params.get("priority"),
            status=params.get("status"),
            assignee_id=int(params["assigneeId"]) if params.get("assigneeId") and params[
                "assigneeId"] != "ALL" else None,
            due_from=datetime.fromisoformat(params["dueFrom"]) if params.get("dueFrom") else None,
            due_to=datetime.fromisoformat(params["dueTo"]) if params.get("dueTo") else None,
        )
        return rows, total, page, page_size

    async def create(self, project_id: int, payload: TaskCreate):
        obj = await self.repo.create(
            project_id=project_id,
            title=payload.title,
            description=payload.description,
            type_=payload.type,
            priority=payload.priority,
            status=payload.status,
            assignee_id=payload.assignee_id,
            due_date=payload.due_date,
        )
        return obj

    async def get(self, task_id: int):
        return await self.repo.get(task_id)

    async def update(self, task_id: int, payload: TaskUpdate):
        data = payload.model_dump(exclude_unset=True)
        version = data.pop("version", None)
        return await self.repo.update(task_id, data, version)

    async def delete(self, task_id: int):
        await self.repo.soft_delete(task_id)

    async def bulk_delete(self, ids: list[int]) -> int:
        return await self.repo.bulk_soft_delete(ids)
