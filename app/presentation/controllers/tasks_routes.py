from fastapi import APIRouter, Depends, Query, HTTPException, status, Body, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from typing import Annotated
from pydantic import BaseModel
from app.presentation.schemas.tasks_schema import TaskCreate, TaskOut, TaskUpdate, PagedTasks
from app.application.services.tasks_service import TaskService
from app.core.db import get_session
from app.presentation.dependencies.auth import get_current_user  # your existing deps

task_router = APIRouter(prefix="/tasks", tags=["tasks"])

DbDep = Annotated[AsyncSession, Depends(get_session)]
UserDep = Annotated[dict, Depends(get_current_user)]


def svc(db: DbDep) -> TaskService:
    return TaskService(db)


# ---------- List tasks (paged) ----------
@task_router.get("/projects/{project_id}/tasks", response_model=PagedTasks, operation_id="projects_tasks_list")
async def list_tasks(
        project_id: int = Path(..., ge=1),
        search: str | None = Query(None),
        type: str | None = Query(None, alias="type"),
        priority: str | None = Query(None),
        status: str | None = Query(None),
        assigneeId: str | None = Query(None),
        dueFrom: str | None = Query(None),
        dueTo: str | None = Query(None),
        page: int = Query(1, ge=1),
        pageSize: int = Query(10, ge=1, le=100),
        db: AsyncSession = Depends(get_session),
        user: dict = Depends(get_current_user),
):
    # RBAC example: only members can read
    # await require_roles(user, allowed={"admin", "project_manager", "member"})
    service = TaskService(db)
    rows, total, p, ps = await service.list_task(
        project_id,
        {
            "search": search,
            "type": type,
            "priority": priority,
            "status": status,
            "assigneeId": assigneeId,
            "dueFrom": dueFrom,
            "dueTo": dueTo,
            "page": page,
            "pageSize": pageSize,
        },
    )
    return {"items": rows, "total": total, "page": p, "page_size": ps}


# ---------- Create task ----------
@task_router.post("/projects/{project_id}/tasks", operation_id="projects_tasks_create", response_model=TaskOut,
                  status_code=status.HTTP_201_CREATED)
async def create_task(
        project_id: int,
        payload: TaskCreate,
        db: AsyncSession = Depends(get_session),
        user: dict = Depends(get_current_user),

):
    # await require_roles(user, allowed={"admin", "project_manager"})
    service = TaskService(db)
    try:
        obj = await service.create(project_id, payload)
        await db.commit()
        return obj
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e.orig))


# ---------- Get task by id ----------
@task_router.get("/tasks/{task_id}", response_model=TaskOut, operation_id="projects_tasks_get_one", )
async def get_task(
        task_id: int,
        db: AsyncSession = Depends(get_session),
        user: dict = Depends(get_current_user),
):
    service = TaskService(db)
    try:
        obj = await service.get(task_id)
        return obj
    except Exception:
        raise HTTPException(status_code=404, detail="Task not found")


# ---------- Update (partial) with optimistic concurrency ----------
@task_router.patch("/tasks/{task_id}", response_model=TaskOut, operation_id="projects_tasks_update", )
async def update_task(
        task_id: int,
        payload: TaskUpdate,
        db: AsyncSession = Depends(get_session),
        user: dict = Depends(get_current_user)

):
    # await require_roles(user, allowed={"admin", "project_manager"})
    service = TaskService(db)
    try:
        obj = await service.update(task_id, payload)
        await db.commit()
        return obj
    except StaleDataError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e.orig))


# ---------- Delete (soft) ----------
@task_router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="projects_tasks_delete", )
async def delete_task(
        task_id: int,
        db: AsyncSession = Depends(get_session),
        user: dict = Depends(get_current_user)

):
    # await require_roles(user, allowed={"admin", "project_manager"})
    service = TaskService(db)
    await service.delete(task_id)
    await db.commit()
    return


# ---------- Bulk delete ----------
class BulkDeleteIn(BaseModel):
    ids: list[int]


from pydantic import BaseModel


@task_router.post("/tasks/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_tasks(
        body: BulkDeleteIn,
        db: AsyncSession = Depends(get_session),
        user: dict = Depends(get_current_user)

):
    # await require_roles(user, allowed={"admin", "project_manager"})
    service = TaskService(db)
    deleted = await service.bulk_delete(body.ids)
    await db.commit()
    if deleted == 0:
        # to align with your preference for actionable errors
        raise HTTPException(status_code=404, detail="No matching tasks found or already deleted")
    return
