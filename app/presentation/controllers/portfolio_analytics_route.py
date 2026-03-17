from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.analytics.portfolio_analytics_usecase import PortfolioAnalyticsService
from app.core.db import get_session
from app.infrastructure.repositories.portfolio_analytics_repository_sqlalchemy import PortfolioAnalyticsRepository
from app.presentation.schemas.portfolio_analytics_schema import (
    PortfolioSummaryOut, PortfolioBreakdownOut, PortfolioCasesWithoutStepsOut,
    PortfolioTrendOut, PortfolioTopProjectsOut, PortfolioCategoryProjectsByStatusOut
)

p_router = APIRouter(prefix="/analytics/portfolios", tags=["portfolio analytics"])


def svp(session: AsyncSession) -> PortfolioAnalyticsRepository:
    return PortfolioAnalyticsRepository(session)


def svc(session: AsyncSession) -> PortfolioAnalyticsService:
    return PortfolioAnalyticsService(PortfolioAnalyticsRepository(session))


@p_router.get("/{portfolio_id}/summary", response_model=PortfolioSummaryOut)
async def portfolio_summary(
        portfolio_id: int,
        include_deleted: bool = Query(False),
        session: AsyncSession = Depends(get_session),
) -> PortfolioSummaryOut:
    return await svc(session).get_summary(portfolio_id, include_deleted)


@p_router.get("/{portfolio_id}/breakdowns", response_model=PortfolioBreakdownOut)
async def portfolio_breakdowns(
        portfolio_id: int,
        include_deleted: bool = Query(False),
        include_nulls: bool = Query(False),
        session: AsyncSession = Depends(get_session),
) -> PortfolioBreakdownOut:
    return await svc(session).get_breakdowns(portfolio_id, include_deleted, include_nulls)


@p_router.get("/{portfolio_id}/quality/without-steps", response_model=PortfolioCasesWithoutStepsOut)
async def portfolio_cases_without_steps(
        portfolio_id: int,
        include_deleted: bool = Query(False),
        limit: int = Query(50, ge=1, le=1000),
        session: AsyncSession = Depends(get_session),
) -> PortfolioCasesWithoutStepsOut:
    return await svc(session).get_cases_without_steps(portfolio_id, include_deleted, limit)


@p_router.get("/{portfolio_id}/trend", response_model=PortfolioTrendOut)
async def portfolio_trend(
        portfolio_id: int,
        include_deleted: bool = Query(False),
        bucket: str = Query("day", pattern="^(day|week|month)$"),
        start_date: Optional[date] = Query(None),
        end_date: Optional[date] = Query(None),
        session: AsyncSession = Depends(get_session),
) -> PortfolioTrendOut:
    return await svc(session).get_trend(portfolio_id, include_deleted, bucket, start_date, end_date)


@p_router.get("/{portfolio_id}/top-projects", response_model=PortfolioTopProjectsOut)
async def portfolio_top_projects(
        portfolio_id: int,
        include_deleted: bool = Query(False),
        limit: int = Query(10, ge=1, le=100),
        session: AsyncSession = Depends(get_session),
) -> PortfolioTopProjectsOut:
    return await svc(session).get_top_projects(portfolio_id, include_deleted, limit)


@p_router.get(
    "/portfolio-categories/projects-by-status",
    response_model=PortfolioCategoryProjectsByStatusOut,
    summary="Projects count by Portfolio Category (Product House) and status for a given year",
)
async def portfolio_category_projects_by_status(
        year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
        session: AsyncSession = Depends(get_session),
):
    return await svp(session).get_projects_by_portfolio_category_and_status(year=year)
