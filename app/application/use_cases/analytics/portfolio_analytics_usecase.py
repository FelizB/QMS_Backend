from datetime import date

from app.infrastructure.repositories.portfolio_analytics_repository_sqlalchemy import PortfolioAnalyticsRepository
from app.presentation.schemas.portfolio_analytics_schema import (
    PortfolioSummaryOut, PortfolioBreakdownOut, LabeledCount,
    PortfolioCasesWithoutStepsOut, PortfolioTrendOut, PortfolioTrendPointOut,
    PortfolioTopProjectsOut
)


class PortfolioAnalyticsService:
    def __init__(self, repo: PortfolioAnalyticsRepository):
        self.repo = repo

    async def get_summary(self, portfolio_id: int, include_deleted: bool = False) -> PortfolioSummaryOut:
        total_programs, total_projects, total_tc, active_tc, deleted_tc = await self.repo.portfolio_summary(
            portfolio_id, include_deleted
        )
        return PortfolioSummaryOut(
            portfolio_id=portfolio_id,
            include_deleted=include_deleted,
            total_programs=total_programs,
            total_projects=total_projects,
            total_test_cases=total_tc,
            active_test_cases=active_tc,
            deleted_test_cases=deleted_tc,
        )

    async def get_breakdowns(
            self, portfolio_id: int, include_deleted: bool = False, include_nulls: bool = False
    ) -> PortfolioBreakdownOut:
        pr = await self.repo.breakdown_priority(portfolio_id, include_deleted, include_nulls)
        ty = await self.repo.breakdown_type(portfolio_id, include_deleted, include_nulls)
        st = await self.repo.breakdown_status(portfolio_id, include_deleted, include_nulls)
        return PortfolioBreakdownOut(
            portfolio_id=portfolio_id,
            include_deleted=include_deleted,
            by_priority=[LabeledCount(id=i, label=lbl, count=cnt, sort_order=so) for (i, lbl, cnt, so) in pr],
            by_type=[LabeledCount(id=i, label=lbl, count=cnt, sort_order=so) for (i, lbl, cnt, so) in ty],
            by_status=[LabeledCount(id=i, label=lbl, count=cnt, sort_order=so) for (i, lbl, cnt, so) in st],
        )

    async def get_cases_without_steps(
            self, portfolio_id: int, include_deleted: bool = False, limit: int = 50
    ) -> PortfolioCasesWithoutStepsOut:
        count, rows = await self.repo.cases_without_steps(portfolio_id, include_deleted, limit)
        items = [
            {"test_case_id": tc_id, "project_id": pid, "name": name, "created_at": created_at}
            for (tc_id, pid, name, created_at) in rows
        ]
        return PortfolioCasesWithoutStepsOut(
            portfolio_id=portfolio_id, include_deleted=include_deleted, count=count, items=items
        )

    async def get_trend(
            self, portfolio_id: int, include_deleted: bool = False, bucket: str = "day",
            start_date: date | None = None, end_date: date | None = None
    ) -> PortfolioTrendOut:
        tuples = await self.repo.test_case_trend(portfolio_id, include_deleted, bucket, start_date, end_date)
        return PortfolioTrendOut(
            portfolio_id=portfolio_id,
            include_deleted=include_deleted,
            bucket=bucket,
            points=[PortfolioTrendPointOut(bucket_start=d, count=c) for (d, c) in tuples],
        )

    async def get_top_projects(
            self, portfolio_id: int, include_deleted: bool = False, limit: int = 10
    ) -> PortfolioTopProjectsOut:
        rows = await self.repo.top_projects(portfolio_id, include_deleted, limit)
        items = [{"project_id": pid, "project_name": name, "test_case_count": cnt} for (pid, name, cnt) in rows]
        return PortfolioTopProjectsOut(
            portfolio_id=portfolio_id, include_deleted=include_deleted, limit=limit, items=items
        )
