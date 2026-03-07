# app/application/services/projects_analytics_service.py
from __future__ import annotations
from datetime import date
from calendar import monthrange
from typing import List, Dict, Any

from app.infrastructure.repositories.analytics_repository_sqlalchemy import \
    ProjectAnalyticsRepository as AnalyticsRepository
from app.presentation.schemas.analytics_schema import MonthlyCreationsOut, MonthlyCreationItem

from datetime import date, datetime, timezone
from typing import Tuple

from app.infrastructure.repositories.dashboard_analytics_sqlalchemy import DashboardRepository
from app.presentation.schemas.analytics_schema import (
    DashboardSummaryOut, EntitySummaryOut, PeriodOut
)


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self.repo = repo

    @staticmethod
    def _first_of_month(y: int, m: int) -> date:
        return date(y, m, 1)

    async def get_monthly_creations(
            self, year: int, include_deleted: bool = False
    ) -> MonthlyCreationsOut:
        portfolios = await self.repo.monthly_portfolio_creations(year, include_deleted)
        programs = await self.repo.monthly_program_creations(year, include_deleted)
        projects = await self.repo.monthly_project_creations(year, include_deleted)

        items: List[MonthlyCreationItem] = []
        for m in range(1, 13):
            first = self._first_of_month(year, m)
            items.append(
                MonthlyCreationItem(
                    month=first.strftime("%Y-%m"),
                    portfolios=portfolios.get(first, 0),
                    programs=programs.get(first, 0),
                    projects=projects.get(first, 0),
                )
            )

        return MonthlyCreationsOut(year=year, items=items)

    async def get_projects_monthly(self, year: int | None = None) -> Dict[str, Any]:
        if year is None:
            year = datetime.now(timezone.utc).year

        items = await self.repo.get_projects_monthly(year)

        total_created = sum(i["created"] for i in items)
        total_active_of_created = sum(i["active_of_created"] for i in items)

        return {
            "year": year,
            "items": items,
            "total_created": total_created,
            "total_active_of_created": total_active_of_created,
        }


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def next_month_start(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def prev_month_start(d: date) -> date:
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def pct_change(curr: int, prev: int) -> float | None:
    if prev == 0:
        return None
    return ((curr - prev) / prev) * 100.0
