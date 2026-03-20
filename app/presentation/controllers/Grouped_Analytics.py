# app/presentation/controllers/analytics_trends_routes.py
from __future__ import annotations
from datetime import date, datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
from app.core.db import get_session
from app.infrastructure.repositories.activity_log_repo_sqlalchemy import ActivityLogRepository as ActivityRepository
from app.infrastructure.repositories.analytics_repository_sqlalchemy import \
    ProjectAnalyticsRepository as AnalyticsRepository, ProjectAnalyticsRepository
from app.application.services.analytics_service import AnalyticsService
from app.infrastructure.repositories.dashboard_analytics_sqlalchemy import DashboardRepository
from app.presentation.schemas.analytics_schema import MonthlyCreationsOut, RecentFeedsOut, TopProjectsOut, \
    RecentProjectCreationsOut
from app.application.services.dashboard_service import DashboardService
from app.presentation.schemas.analytics_schema import DashboardSummaryOut

group_router = APIRouter(prefix="/api/v1/analytics", tags=["dashboard analytics"])


@group_router.get(
    "/org/creations-monthly",
    response_model=MonthlyCreationsOut,
    summary="Monthly creations of portfolios, programs, projects",
)
async def get_org_creations_monthly(
        year: Annotated[int | None, Query(
            description="Year to report. If omitted, defaults to the current year.",
            ge=2000,
            le=2100,
            examples=[2025, 2026],
        )] = None,
        include_deleted: Annotated[bool, Query(
            description="Include soft-deleted rows if applicable."
        )] = False,
        session: AsyncSession = Depends(get_session),
):
    if year is None:
        year = date.today().year
    service = AnalyticsService(session)
    return await service.get_monthly_creations(
        year=year,
        include_deleted=include_deleted,
    )


@group_router.get("/dashboard/summary", response_model=DashboardSummaryOut,
                  summary="Dashboard summary: totals + monthly deltas")
async def dashboard_summary(
        session: AsyncSession = Depends(get_session),
):
    svc = DashboardService(DashboardRepository(session))
    return await svc.get_summary()


@group_router.get("/feeds/recent", response_model=RecentFeedsOut, summary="Recent unified activity feed")
async def get_recent_feeds(
        limit: int = Query(20, ge=1, le=100),
        since: Optional[datetime] = Query(None),
        org_id: Optional[int] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    svc = AnalyticsService(session)
    return await svc.recent_feeds(limit=limit, since=since, org_id=org_id)


@group_router.get("/projects/top", response_model=TopProjectsOut,
                  summary="Top projects by updates with execution progress")
async def get_top_projects(
        limit: int = Query(4, ge=1, le=50),
        window_days: int = Query(7, ge=1, le=90, description="Activity window in days"),
        org_id: Optional[int] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    svc = AnalyticsService(session)
    return await svc.top_projects(limit=limit, window_days=window_days, org_id=org_id)


@group_router.get("/projects/recent-creations", response_model=RecentProjectCreationsOut,
                  summary="Recent project creations")
async def get_recent_creations(
        limit: int = Query(5, ge=1, le=100),
        org_id: Optional[int] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    svc = AnalyticsService(session)
    out = await svc.recent_project_creations(limit=limit, org_id=org_id)
    # Debug guard: make sure we never return None to FastAPI
    assert out is not None, "recent_project_creations returned None"
    return out
