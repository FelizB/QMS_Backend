from __future__ import annotations
from datetime import datetime
from typing import Iterable, Tuple, Sequence
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.tasks_model import Task
from app.infrastructure.models.project_model import Project  # assumed existing
from app.infrastructure.models.user_model import User  # assumed existing
from app.domain.enum import TaskPriority, TaskStatus, TaskType


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_project_active(self, project_id: int) -> None:
        q = select(Project.project_id).where(Project.project_id == project_id, Project.deleted_at.is_(None))
        if not (await self.db.execute(q)).scalar_one_or_none():
            raise NoResultFound("Project not found or deleted")

    def _filters(
            self,
            project_id: int,
            search: str | None,
            type_: TaskType | str | None,
            priority: TaskPriority | str | None,
            status: TaskStatus | str | None,
            assignee_id: int | None,
            due_from: datetime | None,
            due_to: datetime | None,
    ):
        conds = [Task.deleted_at.is_(None), Task.project_id == project_id]
        if search:
            like = f"%{search}%"
            conds.append(or_(Task.title.ilike(like), Task.description.ilike(like)))
        if type_ and type_ != "ALL":
            conds.append(Task.type == type_)
        if priority and priority != "ALL":
            conds.append(Task.priority == priority)
        if status and status != "ALL":
            conds.append(Task.status == status)
        if assignee_id and str(assignee_id) != "ALL":
            conds.append(Task.assignee_id == assignee_id)
        if due_from:
            conds.append(Task.due_date >= due_from)
        if due_to:
            conds.append(Task.due_date <= due_to)
        return and_(*conds)

    async def list_paged(
            self,
            project_id: int,
            page: int,
            page_size: int,
            *,
            search: str | None = None,
            type_: str | None = None,
            priority: str | None = None,
            status: str | None = None,
            assignee_id: int | None = None,
            due_from: datetime | None = None,
            due_to: datetime | None = None,
    ) -> Tuple[Sequence[Task], int]:
        await self.ensure_project_active(project_id)

        cond = self._filters(project_id, search, type_, priority, status, assignee_id, due_from, due_to)

        total = await self.db.scalar(select(func.count()).select_from(Task).where(cond))
        if not total:
            return [], 0

        q = (
            select(Task)
            .options(joinedload(Task.assignee))
            .where(cond)
            .order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(q)).scalars().all()
        return rows, int(total)

    async def create(
            self,
            project_id: int,
            *,
            title: str,
            description: str | None,
            type_: TaskType,
            priority: TaskPriority,
            status: TaskStatus,
            assignee_id: int | None,
            due_date: datetime | None,
    ) -> Task:
        await self.ensure_project_active(project_id)
        obj = Task(
            project_id=project_id,
            title=title,
            description=description,
            type=type_,
            priority=priority,
            status=status,
            assignee_id=assignee_id,
            due_date=due_date,
        )
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get(self, task_id: int) -> Task:
        q = select(Task).options(joinedload(Task.assignee)).where(Task.id == task_id, Task.deleted_at.is_(None))
        obj = (await self.db.execute(q)).scalars().first()
        if not obj:
            raise NoResultFound("Task not found")
        return obj

    async def update(self, task_id: int, data: dict, version: int | None) -> Task:
        obj = await self.get(task_id)
        # optimistic concurrency: if version provided and mismatch, fail early
        if version is not None and obj.version != version:
            from sqlalchemy.orm.exc import StaleDataError
            raise StaleDataError(f"Version mismatch: expected {obj.version}, got {version}")

        for k, v in data.items():
            setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def soft_delete(self, task_id: int) -> None:
        obj = await self.get(task_id)
        obj.deleted_at = datetime.utcnow()
        await self.db.flush()

    async def bulk_soft_delete(self, ids: Iterable[int]) -> int:
        count = 0
        for i in ids:
            try:
                await self.soft_delete(i)
                count += 1
            except NoResultFound:
                continue
        return count
