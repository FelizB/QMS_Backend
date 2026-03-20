import asyncio
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.projects.create_project import CreateProjectUseCase
from app.application.use_cases.projects.delete_project import DeleteProjectUseCase
from app.application.use_cases.projects.get_project import GetProjectUseCase
from app.application.use_cases.projects.list_projects import ListProjectsUseCase
from app.application.use_cases.projects.refresh_caches import RefreshProjectCachesUseCase
from app.application.use_cases.projects.update_project import UpdateProjectUseCase
from app.core.db import get_session
from app.infrastructure.repositories.program_repository_sqlalchemy import ProgramRepository
from app.infrastructure.repositories.project_repository_sqlalchemy import SQLAlchemyProjectRepository
from app.presentation.schemas.project_schema import (
    ProjectCreate,
    ProjectUpdate,
    ProjectOut,
    ProjectSummary,
    ProjectDeleteOut,
)
from app.presentation.dependencies.role_permissions import require_role_action as require_permission
from app.domain.enum import EntityType, Action, ApprovalStatus
from app.infrastructure.models.approval import ApprovalRequest
from app.infrastructure.models.activity_log import ActivityLog as AuditLog

projects_router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyProjectRepository(session)


def get_program_repo(session: AsyncSession = Depends(get_session)) -> ProgramRepository:
    return ProgramRepository(session)


# ---------- Helpers ----------

class ApprovalQueuedOut(BaseModel):
    message: Literal["queued-for-approval"]
    approval_id: int


def _dump(model) -> dict:
    """Safe Pydantic v2 dump (no None values)."""
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    try:
        return dict(model)
    except Exception:
        return {}


async def _audit(
        session: AsyncSession,
        *,
        actor_id: int,
        action: str,  # e.g., "project.create"
        entity_type: str,  # e.g., EntityType.PROJECT
        entity_id: Optional[int],
        result: Literal["success", "failure", "queued"],
        meta: Optional[dict] = None,
):
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            status=result,
            meta=meta or {},
        )
    )
    # Route will commit once per request


# ---------- CREATE (maker-checker aware) ----------

@projects_router.post(
    "",
    response_model=ProjectOut | ApprovalQueuedOut,
    status_code=status.HTTP_201_CREATED,
    responses={202: {"model": ApprovalQueuedOut}},
)
async def create_project(
        payload: ProjectCreate,
        repo=Depends(get_project_repo),
        program_repo: ProgramRepository = Depends(get_program_repo),
        session: AsyncSession = Depends(get_session),
        perm=Depends(require_permission(EntityType.PROJECT, Action.CREATE)),
):
    user = perm["user"]
    mkc_required: bool = perm["mkc_required"]

    # FK/soft-delete guard
    program_id = payload.program_id
    program = await program_repo.get(program_id)
    if not program or getattr(program, "is_deleted", False):
        await _audit(
            session,
            actor_id=user.id,
            action="project.create",
            entity_type=EntityType.PROJECT,
            entity_id=None,
            result="failure",
            meta={"reason": f"program {program_id} not found"},
        )
        await session.commit()
        raise HTTPException(status_code=404, detail=f"Program {program_id} not found")

    if mkc_required:
        ar = ApprovalRequest(
            entity_type=EntityType.PROJECT,
            entity_id=None,
            action=Action.CREATE,
            payload_before=None,
            payload_after=_dump(payload),
            status=ApprovalStatus.PENDING,
            maker_id=user.id,
            requires_maker_checker=True,
        )
        session.add(ar)
        await _audit(
            session,
            actor_id=user.id,
            action="project.create",
            entity_type=EntityType.PROJECT,
            entity_id=None,
            result="queued",
            meta={"program_id": program_id},
        )
        await session.flush()
        await session.commit()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ApprovalQueuedOut(
                message="queued-for-approval", approval_id=ar.id
            ).model_dump(),
        )

    # Immediate path
    uc = CreateProjectUseCase(repo)
    out = await uc.execute(payload)
    if not out:
        await _audit(
            session,
            actor_id=user.id,
            action="project.create",
            entity_type=EntityType.PROJECT,
            entity_id=None,
            result="failure",
            meta={"reason": "create_failed"},
        )
        await session.commit()
        raise HTTPException(status_code=404, detail="unable to create project")

    await _audit(
        session,
        actor_id=user.id,
        action="project.create",
        entity_type=EntityType.PROJECT,
        entity_id=getattr(out, "id", None),
        result="success",
        meta={"program_id": program_id},
    )
    await session.commit()
    return out


# ---------- Refresh caches (unchanged) ----------

@projects_router.post("/{project_id}/refresh-caches", status_code=status.HTTP_202_ACCEPTED)
async def refresh_caches_all(
        project_id: int,
        run_async: bool = Query(default=True),
):
    uc = RefreshProjectCachesUseCase()
    if run_async:
        asyncio.create_task(uc.execute(project_id, None, True))
        return {"project_id": project_id, "status": "queued"}
    else:
        return await uc.execute(project_id, None, False)


@projects_router.post("/{project_id}/refresh-caches/{release_id}", status_code=status.HTTP_202_ACCEPTED)
async def refresh_caches_release(
        project_id: int,
        release_id: int,
        run_async: bool = Query(default=True),
):
    uc = RefreshProjectCachesUseCase()
    if run_async:
        asyncio.create_task(uc.execute(project_id, release_id, True))
        return {"project_id": project_id, "release_id": release_id, "status": "queued"}
    else:
        return await uc.execute(project_id, release_id, False)


# ---------- Unchanged: list / get ----------

@projects_router.get("", response_model=list[ProjectSummary])
async def list_projects(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        repo=Depends(get_project_repo),
):
    uc = ListProjectsUseCase(repo)
    return await uc.execute(limit=limit, offset=offset)


@projects_router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, repo=Depends(get_project_repo)):
    uc = GetProjectUseCase(repo)
    out = await uc.execute_full(project_id)
    if not out:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


# ---------- DELETE (maker-checker aware) ----------

@projects_router.delete(
    "/{project_id}",
    response_model=ProjectDeleteOut | ApprovalQueuedOut,
    responses={202: {"model": ApprovalQueuedOut}},
)
async def delete_project(
        project_id: int,
        repo=Depends(get_project_repo),
        session: AsyncSession = Depends(get_session),
        perm=Depends(require_permission(EntityType.PROJECT, Action.DELETE)),
):
    user = perm["user"]
    mkc_required: bool = perm["mkc_required"]

    # BEFORE snapshot (for audit or queued delete)
    before_uc = GetProjectUseCase(repo)
    before = await before_uc.execute_full(project_id)
    if not before:
        await _audit(
            session,
            actor_id=user.id,
            action="project.delete",
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            result="failure",
            meta={"reason": "not_found"},
        )
        await session.commit()
        raise HTTPException(status_code=404, detail="Project not found")

    if mkc_required:
        ar = ApprovalRequest(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            action=Action.DELETE,
            payload_before=_dump(before),
            payload_after=None,
            status=ApprovalStatus.PENDING,
            maker_id=user.id,
            requires_maker_checker=True,
        )
        session.add(ar)
        await _audit(
            session,
            actor_id=user.id,
            action="project.delete",
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            result="queued",
            meta=None,
        )
        await session.flush()
        await session.commit()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ApprovalQueuedOut(
                message="queued-for-approval", approval_id=ar.id
            ).model_dump(),
        )

    # Immediate path
    uc = DeleteProjectUseCase(repo)
    ok = await uc.execute(project_id)
    if not ok:
        await _audit(
            session,
            actor_id=user.id,
            action="project.delete",
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            result="failure",
            meta={"reason": "delete_failed"},
        )
        await session.commit()
        raise HTTPException(status_code=404, detail="Project not found")

    await _audit(
        session,
        actor_id=user.id,
        action="project.delete",
        entity_type=EntityType.PROJECT,
        entity_id=project_id,
        result="success",
        meta=None,
    )
    await session.commit()
    return ok


# ---------- UPDATE (maker-checker aware) ----------

@projects_router.put(
    "/{project_id}",
    response_model=ProjectOut | ApprovalQueuedOut,
    responses={202: {"model": ApprovalQueuedOut}},
)
async def update_project(
        project_id: int,
        payload: ProjectUpdate,
        repo=Depends(get_project_repo),
        session: AsyncSession = Depends(get_session),
        perm=Depends(require_permission(EntityType.PROJECT, Action.UPDATE)),
):
    user = perm["user"]
    mkc_required: bool = perm["mkc_required"]

    # BEFORE snapshot
    before_uc = GetProjectUseCase(repo)
    before = await before_uc.execute_full(project_id)

    if not before:
        await _audit(
            session,
            actor_id=user.id,
            action="project.update",
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            result="failure",
            meta={"reason": "not_found"},
        )
        await session.commit()
        raise HTTPException(status_code=404, detail="Project not found")

    if mkc_required:
        ar = ApprovalRequest(
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            action=Action.UPDATE,
            payload_before=_dump(before),
            payload_after=_dump(payload),
            status=ApprovalStatus.PENDING,
            maker_id=user.id,
            requires_maker_checker=True,
        )
        session.add(ar)
        await _audit(
            session,
            actor_id=user.id,
            action="project.update",
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            result="queued",
            meta={"fields": list(_dump(payload).keys())},
        )
        await session.flush()
        await session.commit()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ApprovalQueuedOut(
                message="queued-for-approval", approval_id=ar.id
            ).model_dump(),
        )

    # Immediate path
    uc = UpdateProjectUseCase(repo)
    out = await uc.execute(project_id, payload)
    if not out:
        await _audit(
            session,
            actor_id=user.id,
            action="project.update",
            entity_type=EntityType.PROJECT,
            entity_id=project_id,
            result="failure",
            meta={"reason": "update_failed"},
        )
        await session.commit()
        raise HTTPException(status_code=404, detail="Project not found")

    await _audit(
        session,
        actor_id=user.id,
        action="project.update",
        entity_type=EntityType.PROJECT,
        entity_id=project_id,
        result="success",
        meta={"fields": list(_dump(payload).keys())},
    )
    await session.commit()
    return out
