from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.analytics.programs_analytics_usecase import ProgramAnalyticsService
from app.core.db import get_session
from app.infrastructure.repositories.program_analytics_repo_sqlalchemy import ProgramAnalyticsRepository
from app.presentation.schemas.program_analytics_schema import (
    ProgramSummaryOut, ProgramBreakdownOut, ProgramCasesWithoutStepsOut, ProgramTrendOut, ProgramTopProjectsOut
)

program_a_router = APIRouter(prefix="/analytics/programs", tags=["program analytics"])


def svc(session: AsyncSession) -> ProgramAnalyticsService:
    return ProgramAnalyticsService(ProgramAnalyticsRepository(session))


@program_a_router.get("/{program_id}/summary", response_model=ProgramSummaryOut)
async def program_summary(
        program_id: int,
        include_deleted: bool = Query(False),
        session: AsyncSession = Depends(get_session),
) -> ProgramSummaryOut:
    return await svc(session).get_summary(program_id, include_deleted)


@program_a_router.get("/{program_id}/breakdowns", response_model=ProgramBreakdownOut)
async def program_breakdowns(
        program_id: int,
        include_deleted: bool = Query(False),
        include_nulls: bool = Query(False),
        session: AsyncSession = Depends(get_session),
) -> ProgramBreakdownOut:
    return await svc(session).get_breakdowns(program_id, include_deleted, include_nulls)


@program_a_router.get("/{program_id}/quality/without-steps", response_model=ProgramCasesWithoutStepsOut)
async def program_cases_without_steps(
        program_id: int,
        include_deleted: bool = Query(False),
        limit: int = Query(50, ge=1, le=1000),
        session: AsyncSession = Depends(get_session),
) -> ProgramCasesWithoutStepsOut:
    return await svc(session).get_cases_without_steps(program_id, include_deleted, limit)


@program_a_router.get("/{program_id}/trend", response_model=ProgramTrendOut)
async def program_trend(
        program_id: int,
        include_deleted: bool = Query(False),
        bucket: str = Query("day", pattern="^(day|week|month)$"),
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        session: AsyncSession = Depends(get_session),
) -> ProgramTrendOut:
    return await svc(session).get_trend(program_id, include_deleted, bucket, start_date, end_date)


@program_a_router.get("/{program_id}/top-projects", response_model=ProgramTopProjectsOut)
async def program_top_projects(
        program_id: int,
        include_deleted: bool = Query(False),
        limit: int = Query(10, ge=1, le=100),
        session: AsyncSession = Depends(get_session),
) -> ProgramTopProjectsOut:
    return await svc(session).get_top_projects(program_id, include_deleted, limit)
