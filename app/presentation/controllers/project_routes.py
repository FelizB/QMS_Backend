import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.presentation.schemas.project_schema import (ProjectCreate, ProjectUpdate, ProjectOut, ProjectSummary,
                                                     ProjectDeleteOut)

projects_router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyProjectRepository(session)


def get_program_repo(session: AsyncSession = Depends(get_session)) -> ProgramRepository:
    return ProgramRepository(session)


@projects_router.get("", response_model=list[ProjectSummary])
async def list_projects(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        repo=Depends(get_project_repo)
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


@projects_router.delete("/{project_id}", response_model=ProjectDeleteOut)
async def delete_project(project_id: int, repo=Depends(get_project_repo)):
    uc = DeleteProjectUseCase(repo)
    ok = await uc.execute(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return ok


@projects_router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: int, payload: ProjectUpdate, repo=Depends(get_project_repo)):
    uc = UpdateProjectUseCase(repo)
    out = await uc.execute(project_id, payload)
    if not out:
        raise HTTPException(status_code=404, detail="Project not found")
    return out


@projects_router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
        payload: ProjectCreate,
        repo=Depends(get_project_repo),
        program_repo: ProgramRepository = Depends(get_program_repo)
):
    program_id = payload.program_id
    program = await program_repo.get(program_id)
    if not program or getattr(program, "is_deleted", False):
        raise HTTPException(status_code=404, detail=f"Program {program_id} not found")

    uc = CreateProjectUseCase(repo)
    out = await uc.execute(payload)
    if not out:
        raise HTTPException(status_code=404, detail="unable to create project")
    return out


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
