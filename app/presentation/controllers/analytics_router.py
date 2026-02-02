from datetime import date
from typing import Optional, Literal, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.analytics.analytics_service import ProjectAnalyticsService
from app.core.db import get_session
from app.infrastructure.repositories.analytics_repository_sqlalchemy import ProjectAnalyticsRepository
from app.presentation.schemas.analytics_schema import TestCaseSummaryOut, TestStepSummaryOut, TrendPointOut, \
    TestCaseBreakdownOut, CasesWithoutStepsOut

analytics_router = APIRouter(prefix="/analytics/projects", tags=["analytics"])


def svc(session: AsyncSession) -> ProjectAnalyticsService:
    return ProjectAnalyticsService(ProjectAnalyticsRepository(session))


@analytics_router.get("/{project_id}/test-cases/summary", response_model=TestCaseSummaryOut)
async def get_test_case_summary(
        project_id: int,
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_test_case_summary(
        project_id, include_deleted, release_id, folder_id
    )


@analytics_router.get("/{project_id}/test-steps/summary", response_model=TestStepSummaryOut)
async def get_test_step_summary(
        project_id: int,
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_test_step_summary(
        project_id, include_deleted, release_id, folder_id
    )


@analytics_router.get("/{project_id}/test-cases/trend", response_model=List[TrendPointOut])
async def get_test_case_trend(
        project_id: int,
        bucket: Literal["day", "week", "month"] = Query("day"),
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_test_case_trend(
        project_id, bucket, start_date, end_date, include_deleted, release_id, folder_id
    )


@analytics_router.get("/{project_id}/test-cases/breakdown", response_model=TestCaseBreakdownOut)
async def get_test_case_breakdown(
        project_id: int,
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        include_nulls: bool = Query(False, description="Include rows where priority/type is NULL"),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_breakdowns(
        project_id=project_id,
        include_deleted=include_deleted,
        release_id=release_id,
        folder_id=folder_id,
        include_nulls=include_nulls,
    )


@analytics_router.get("/{project_id}/test-cases/quality/without-steps", response_model=CasesWithoutStepsOut)
async def get_cases_without_steps(
        project_id: int,
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        include_ids: bool = Query(False, description="Include a list of case ids/names without steps"),
        limit: int = Query(50, ge=1, le=1000),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_cases_without_steps(
        project_id=project_id,
        include_deleted=include_deleted,
        release_id=release_id,
        folder_id=folder_id,
        include_ids=include_ids,
        limit=limit,
    )
