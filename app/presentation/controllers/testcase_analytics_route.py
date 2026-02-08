from typing import Optional

from fastapi import APIRouter, Path, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.analytics.testcase_analytics_usecase import (
    GetCoverage, GetFolderBreakdown, GetStepTrend, GetHealthcard
)
from app.application.use_cases.analytics.testcase_analytics_usecase import (
    GetTestCaseSummary, GetStepExecutionSummary, GetTestCaseTrends, GetTestCaseAging
)
from app.core.db import get_session
from app.presentation.schemas.testcase_analytics_schema import (
    CoverageOut, FolderBreakdownOut, StepTrendOut, HealthcardOut
)
from app.presentation.schemas.testcase_analytics_schema import (
    TestCaseSummaryOut, TestStepsExecutionSummaryOut, TestCaseTrendsOut, TestCaseAgingOut
)

testcase_analytics_router = APIRouter(prefix="/projects/{project_id}/analytics", tags=["TestCase Analytics"])


@testcase_analytics_router.get("/test-cases/summary", response_model=TestCaseSummaryOut)
async def test_case_summary(
        project_id: int = Path(..., gt=0),
        release_id: int | None = Query(None, gt=0, description="Optional release filter"),
        session: AsyncSession = Depends(get_session),
):
    return await GetTestCaseSummary(session)(project_id, release_id)


@testcase_analytics_router.get("/test-steps/execution-summary", response_model=TestStepsExecutionSummaryOut)
async def test_steps_execution_summary(
        project_id: int = Path(..., gt=0),
        release_id: int | None = Query(None, gt=0, description="Optional release filter"),
        session: AsyncSession = Depends(get_session),
):
    return await GetStepExecutionSummary(session)(project_id, release_id)


@testcase_analytics_router.get("/test-cases/trends", response_model=TestCaseTrendsOut)
async def test_case_trends(
        project_id: int = Path(..., gt=0),
        period: str = Query("day", pattern="^(day|week|month)$"),
        date_from: str | None = Query(None, description="YYYY-MM-DD or timestamp (UTC)"),
        date_to: str | None = Query(None, description="YYYY-MM-DD or timestamp (UTC)"),
        session: AsyncSession = Depends(get_session),
):
    return await GetTestCaseTrends(session)(project_id, period, date_from, date_to)


@testcase_analytics_router.get("/test-cases/aging", response_model=TestCaseAgingOut)
async def test_case_aging(
        project_id: int = Path(..., gt=0),
        days_without_update: int = Query(30, ge=1, le=365),
        not_run_id: int = Query(0, description="ExecutionStatus id that represents NOT_RUN"),  # adjust default
        session: AsyncSession = Depends(get_session),
):
    return await GetTestCaseAging(session)(project_id, days_without_update, not_run_id)


@testcase_analytics_router.get("/test-cases/coverage", response_model=CoverageOut)
async def test_case_coverage(
        project_id: int = Path(..., gt=0),
        release_id: Optional[int] = Query(None, gt=0),
        not_run_status_id: Optional[int] = Query(None, description="Execution status id representing NOT_RUN"),
        session: AsyncSession = Depends(get_session),
):
    return await GetCoverage(session)(project_id, release_id, not_run_status_id)


# ----------- Folder breakdown
@testcase_analytics_router.get("/test-cases/by-folder", response_model=FolderBreakdownOut)
async def test_cases_by_folder(
        project_id: int = Path(..., gt=0),
        release_id: Optional[int] = Query(None, gt=0),
        session: AsyncSession = Depends(get_session),
):
    return await GetFolderBreakdown(session)(project_id, release_id)


# ---------------Step execution trend
@testcase_analytics_router.get("/test-steps/trend", response_model=StepTrendOut)
async def step_execution_trend(
        project_id: int = Path(..., gt=0),
        period: str = Query("day", pattern="^(day|week|month)$"),
        release_id: Optional[int] = Query(None, gt=0),
        date_from: Optional[str] = Query(None, description="UTC, e.g., 2026-01-01"),
        date_to: Optional[str] = Query(None, description="UTC exclusive upper bound, e.g., 2026-02-01"),
        session: AsyncSession = Depends(get_session),
):
    return await GetStepTrend(session)(project_id, release_id, period, date_from, date_to)


# ------------------Healthcard (summary + steps + coverage)
@testcase_analytics_router.get("/healthcard", response_model=HealthcardOut)
async def analytics_healthcard(
        project_id: int = Path(..., gt=0),
        release_id: Optional[int] = Query(None, gt=0),
        passed_status_id: Optional[int] = Query(None, description="Step execution status id for 'Passed'"),
        not_run_status_id: Optional[int] = Query(None, description="Step execution status id for 'Not Run'"),
        session: AsyncSession = Depends(get_session),
):
    return await GetHealthcard(session)(project_id, release_id, passed_status_id, not_run_status_id)
