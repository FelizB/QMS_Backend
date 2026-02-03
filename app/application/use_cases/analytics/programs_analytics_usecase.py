from datetime import date
from app.infrastructure.repositories.program_analytics_repo_sqlalchemy import ProgramAnalyticsRepository
from app.presentation.schemas.program_analytics_schema import (
    ProgramSummaryOut, ProgramBreakdownOut, LabeledCount,
    ProgramCasesWithoutStepsOut, ProgramTrendOut, ProgramTrendPointOut,
    ProgramTopProjectsOut
)
from datetime import date

from app.infrastructure.repositories.program_analytics_repo_sqlalchemy import ProgramAnalyticsRepository
from app.presentation.schemas.program_analytics_schema import (
    ProgramSummaryOut, ProgramBreakdownOut, LabeledCount,
    ProgramCasesWithoutStepsOut, ProgramTrendOut, ProgramTrendPointOut,
    ProgramTopProjectsOut
)


class ProgramAnalyticsService:
    def __init__(self, repo: ProgramAnalyticsRepository):
        self.repo = repo

    async def get_summary(self, program_id: int, include_deleted: bool = False) -> ProgramSummaryOut:
        total_projects, total_tc, active_tc, deleted_tc = await self.repo.program_summary(program_id, include_deleted)
        return ProgramSummaryOut(
            program_id=program_id,
            include_deleted=include_deleted,
            total_projects=total_projects,
            total_test_cases=total_tc,
            active_test_cases=active_tc,
            deleted_test_cases=deleted_tc,
        )

    async def get_breakdowns(
            self, program_id: int, include_deleted: bool = False, include_nulls: bool = False
    ) -> ProgramBreakdownOut:
        pr = await self.repo.breakdown_priority(program_id, include_deleted, include_nulls)
        ty = await self.repo.breakdown_type(program_id, include_deleted, include_nulls)
        st = await self.repo.breakdown_status(program_id, include_deleted, include_nulls)
        return ProgramBreakdownOut(
            program_id=program_id,
            include_deleted=include_deleted,
            by_priority=[LabeledCount(id=i, label=lbl, count=cnt, sort_order=so) for (i, lbl, cnt, so) in pr],
            by_type=[LabeledCount(id=i, label=lbl, count=cnt, sort_order=so) for (i, lbl, cnt, so) in ty],
            by_status=[LabeledCount(id=i, label=lbl, count=cnt, sort_order=so) for (i, lbl, cnt, so) in st],
        )

    async def get_cases_without_steps(self, program_id: int, include_deleted: bool = False,
                                      limit: int = 50) -> ProgramCasesWithoutStepsOut:
        count, rows = await self.repo.cases_without_steps(program_id, include_deleted, limit)
        items = [{"test_case_id": tc_id, "project_id": pid, "name": name, "created_at": created_at} for
                 (tc_id, pid, name, created_at) in rows]
        return ProgramCasesWithoutStepsOut(program_id=program_id, include_deleted=include_deleted, count=count,
                                           items=items)

    async def get_trend(
            self, program_id: int, include_deleted: bool = False, bucket: str = "day",
            start_date: date | None = None, end_date: date | None = None
    ) -> ProgramTrendOut:
        tuples = await self.repo.test_case_trend(program_id, include_deleted, bucket, start_date, end_date)
        return ProgramTrendOut(
            program_id=program_id,
            include_deleted=include_deleted,
            bucket=bucket,
            points=[ProgramTrendPointOut(bucket_start=d, count=c) for (d, c) in tuples],
        )

    async def get_top_projects(self, program_id: int, include_deleted: bool = False,
                               limit: int = 10) -> ProgramTopProjectsOut:
        rows = await self.repo.top_projects(program_id, include_deleted, limit)
        items = [{"project_id": pid, "project_name": name, "test_case_count": cnt} for (pid, name, cnt) in rows]
        return ProgramTopProjectsOut(program_id=program_id, include_deleted=include_deleted, limit=limit, items=items)
