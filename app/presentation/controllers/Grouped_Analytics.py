# app/presentation/controllers/analytics_trends_routes.py
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.infrastructure.repositories.analytics_repository_sqlalchemy import \
    ProjectAnalyticsRepository as AnalyticsRepository
from app.application.services.analytics_service import AnalyticsService
from app.infrastructure.repositories.dashboard_analytics_sqlalchemy import DashboardRepository
from app.presentation.schemas.analytics_schema import MonthlyCreationsOut
from app.application.services.dashboard_service import DashboardService
from app.presentation.schemas.analytics_schema import DashboardSummaryOut

group_router = APIRouter(prefix="/api/v1/analytics", tags=["dashboard analytics"])


@group_router.get("/org/creations-monthly", response_model=MonthlyCreationsOut,
                  summary="Monthly creations of portfolios, programs, projects")
async def get_org_creations_monthly(
        year: int = Query(default=None, description="Year (defaults to current year)"),
        include_deleted: bool = Query(default=False, description="Include soft-deleted rows, if applicable"),
        session: AsyncSession = Depends(get_session),
):
    if year is None:
        year = date.today().year

    service = AnalyticsService(AnalyticsRepository(session))
    return await service.get_monthly_creations(year=year, include_deleted=include_deleted)


@group_router.get("/dashboard/summary", response_model=DashboardSummaryOut,
                  summary="Dashboard summary: totals + monthly deltas")
async def dashboard_summary(
        session: AsyncSession = Depends(get_session),
):
    svc = DashboardService(DashboardRepository(session))
    return await svc.get_summary()
