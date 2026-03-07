from datetime import date
from typing import Optional, Literal, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_service import AnalyticsService
from app.application.use_cases.analytics.projects_analytics_service import ProjectAnalyticsService
from app.core.db import get_session
from app.infrastructure.repositories.analytics_repository_sqlalchemy import ProjectAnalyticsRepository
from app.infrastructure.repositories.testcase_analytics_repository_sqlalchemy import AnalyticsRepository
from app.presentation.schemas.analytics_schema import TestCaseSummaryOut, TestStepSummaryOut, TrendPointOut, \
    TestCaseBreakdownOut, CasesWithoutStepsOut, AgingMetricsOut, LongestCasesOut, ReleaseCoverageOut, PriorityHealthOut, \
    TestCaseBreakdownLabeledOut, LabeledCount, ProjectStatusCountsOut, ProjectsMonthlyOut

analytics_router = APIRouter(prefix="/analytics/projects", tags=["project analytics"])


def svc(session: AsyncSession) -> ProjectAnalyticsService:
    return ProjectAnalyticsService(ProjectAnalyticsRepository(session))


def svp(session: AsyncSession) -> ProjectAnalyticsRepository:
    return ProjectAnalyticsRepository(session)


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


#  ---- Aging Cases ----
@analytics_router.get("/{project_id}/test-cases/aging", response_model=AgingMetricsOut)
async def get_aging_metrics(
        project_id: int,
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        stale_days: int = Query(30, ge=1, le=3650, description="Threshold in days for 'stale' counts"),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_aging_metrics(project_id, include_deleted, release_id, folder_id, stale_days)


# ---- Longest cases ----
@analytics_router.get("/{project_id}/test-cases/longest", response_model=LongestCasesOut)
async def get_longest_cases(
        project_id: int,
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        limit: int = Query(20, ge=1, le=500),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_longest_cases(project_id, include_deleted, release_id, folder_id, limit)


# ---- Release coverage ----
@analytics_router.get("/{project_id}/releases/coverage", response_model=ReleaseCoverageOut)
async def get_release_coverage(
        project_id: int,
        include_deleted: bool = Query(False),
        session: AsyncSession = Depends(get_session),
):
    return await svc(session).get_release_coverage(project_id, include_deleted)


# ---- Priority health ----
def parse_csv_ints(csv: Optional[str]) -> List[int]:
    if not csv:
        return []
    return [int(x.strip()) for x in csv.split(",") if x.strip().isdigit()]


@analytics_router.get("/{project_id}/test-cases/priority-health", response_model=PriorityHealthOut)
async def get_priority_health(
        project_id: int,
        high_priority_ids: Optional[str] = Query(None,
                                                 description="CSV of priority_id values considered 'high' e.g. '1,2'"),
        include_deleted: bool = Query(False),
        release_id: Optional[int] = Query(None),
        folder_id: Optional[int] = Query(None),
        stale_days: int = Query(30, ge=1, le=3650),
        session: AsyncSession = Depends(get_session),
):
    hp = parse_csv_ints(high_priority_ids) or [1]  # default: priority_id 1
    return await svc(session).get_priority_health(project_id, hp, include_deleted, release_id, folder_id, stale_days)


@analytics_router.get("/{project_id}/test-cases/breakdown-labeled", response_model=TestCaseBreakdownLabeledOut)
async def get_test_case_breakdown_labeled(

        project_id: int,
        include_deleted: bool = False,
        release_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        include_nulls: bool = False,
        session: AsyncSession = Depends(get_session),
) -> TestCaseBreakdownLabeledOut:
    pr = await svp(session).breakdown_by_priority_with_labels(
        project_id, include_deleted, release_id, folder_id, include_nulls
    )
    pv = await svp(session).breakdown_by_priority_with_labels(project_id, include_deleted, release_id, folder_id,
                                                              include_nulls)
    print("PR:", pv, type(pv))
    ty = await svp(session).breakdown_by_type_with_labels(
        project_id, include_deleted, release_id, folder_id, include_nulls
    )
    pr_items = [
        LabeledCount(id=i, label=lbl, count=c, sort_order=so)
        for (i, lbl, c, so) in pr
    ]
    ty_items = [
        LabeledCount(id=i, label=lbl, count=c, sort_order=so)
        for (i, lbl, c, so) in ty
    ]
    print("TR:", ty, type(ty))
    return TestCaseBreakdownLabeledOut(
        project_id=project_id,
        include_deleted=include_deleted,
        by_priority=pr_items,
        by_type=ty_items,
    )


@analytics_router.get("/status-counts", response_model=ProjectStatusCountsOut, summary="Counts of projects by status")
async def projects_status_counts(
        session: AsyncSession = Depends(get_session),
):
    svc = ProjectAnalyticsService(ProjectAnalyticsRepository(session))
    return await svc.get_status_counts()


def get_analytics_service(session: AsyncSession = Depends(get_session)) -> AnalyticsService:
    repo = ProjectAnalyticsRepository(session)
    return AnalyticsService(repo)


@analytics_router.get("/monthly", response_model=ProjectsMonthlyOut)
async def get_projects_monthly(
        year: int | None = Query(None, ge=2000, le=9999),
        svc: AnalyticsService = Depends(get_analytics_service)
):
    """
    Returns monthly counts for projects created and how many of those are active.
    Defaults to current year if `year` is not provided.
    """
    return await svc.get_projects_monthly(year)
