# app/application/services/projects_analytics_service.py# app/application/services/projects_analytics_service.pyOut(items=items, total=len(items))
from datetime import date


# ---------- Standalone helpers (if used elsewhere) ----------
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


from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.activity_log_repo_sqlalchemy import ActivityLogRepository as ActivityRepository
from app.infrastructure.repositories.analytics_repository_sqlalchemy import (
    ProjectAnalyticsRepository,
)
from app.presentation.schemas.analytics_schema import (
    MonthlyCreationsOut,
    MonthlyCreationItem,
    RecentFeedsOut,
    RecentFeedItem,
    TopProjectsOut,
    TopProjectItem,
    RecentProjectCreationsOut,
    RecentProjectCreationItem,
    # If you need dashboard types here later:
    # DashboardSummaryOut, EntitySummaryOut, PeriodOut,
)


class AnalyticsService:
    """
    Service layer for analytics/trends. Construct with a concrete AsyncSession.

    Usage from routes:
        session: AsyncSession = Depends(get_session)
        svc = AnalyticsService(session)
        return await svc.recent_feeds(...)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        # Instantiate repositories with the resolved AsyncSession
        self.activity_repo = ActivityRepository(session)
        self.project_repo = ProjectAnalyticsRepository(session)

    # ---------- Helpers ----------
    @staticmethod
    def _first_of_month(y: int, m: int) -> date:
        return date(y, m, 1)

    # ---------- Public methods ----------
    async def get_monthly_creations(
            self,
            year: int,
            include_deleted: bool = False,
    ) -> MonthlyCreationsOut:
        """
        Returns monthly counts for portfolios, programs, and projects for a given year.
        Expects the repository to return dicts keyed by date(y, m, 1) -> int.
        """
        portfolios = await self.project_repo.monthly_portfolio_creations(year, include_deleted)
        programs = await self.project_repo.monthly_program_creations(year, include_deleted)
        projects = await self.project_repo.monthly_project_creations(year, include_deleted)

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
        """
        Returns:
            {
              "year": int,
              "items": <repo list>,
              "total_created": int,
              "total_active_of_created": int
            }
        """
        if year is None:
            year = datetime.now(timezone.utc).year

        items = await self.project_repo.get_projects_monthly(year)

        total_created = sum(int(i.get("created", 0)) for i in items)
        total_active_of_created = sum(int(i.get("active_of_created", 0)) for i in items)

        return {
            "year": year,
            "items": items,
            "total_created": total_created,
            "total_active_of_created": total_active_of_created,
        }

    async def recent_feeds(
            self,
            limit: int = 20,
            since: Optional[datetime] = None,
            org_id: int | None = None,
    ) -> RecentFeedsOut:
        """
        Unified recent activity feed across entity types from the activity log.
        """
        rows, total = await self.activity_repo.get_recent(limit=limit, since=since, org_id=org_id)
        items = [
            RecentFeedItem(
                title=r["title"],
                actor_first_name=r["actor_first_name"],
                performed_at=r["performed_at"],
                entity_type=r["entity_type"].value if hasattr(r["entity_type"], "value") else r["entity_type"],
                action=r["action"].value if hasattr(r["action"], "value") else r["action"],
                entity_id=r["entity_id"],
            )
            for r in rows
        ]
        return RecentFeedsOut(items=items, total=total)

    async def top_projects(
            self,
            limit: int = 4,
            window_days: int = 7,
            org_id: int | None = None,
    ) -> TopProjectsOut:
        """
        Top projects by activity (updates) with current execution progress and trend.
        Delegates to project_repo.get_top_projects.
        """
        rows = await self.project_repo.get_top_projects(limit=limit, window_days=window_days, org_id=org_id)
        items = [
            TopProjectItem(
                project_id=int(r["project_id"]),
                project_name=str(r["project_name"]),
                testcases_total=int(r["testcases_total"]),
                testcases_executed=int(r["testcases_executed"]),
                progress_percent=float(r["progress_percent"]),
                trend=str(r["trend"]),
                updates_in_window=int(r["updates_in_window"]),
            )
            for r in rows
        ]
        return TopProjectsOut(items=items, total=len(items))

    async def recent_project_creations(
            self,
            limit: int = 5,
            org_id: int | None = None,
    ) -> RecentProjectCreationsOut:
        try:
            rows = await self.project_repo.get_recent_creations(limit=limit, org_id=org_id)
            # Defensive: normalize rows to list
            if rows is None:
                rows = []
            items = [
                RecentProjectCreationItem(
                    id=int(r["id"]),
                    owner_name=r.get("owner_name"),
                    name=str(r["name"]),
                    created_at=r["created_at"],
                    status=str(r["status"]),
                )
                for r in rows
            ]
            return RecentProjectCreationsOut(items=items, total=len(items))
        except Exception as e:
            # Log & return empty payload instead of None to satisfy response_model
            # You can swap print with your logger
            print(f"[recent_project_creations] error: {e}")
            return RecentProjectCreationsOut(items=[], total=0)
