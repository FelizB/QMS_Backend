# app/infrastructure/repositories/portfolio_analytics_repository.py
from datetime import date, datetime
from typing import List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.lookup_model import PriorityLkp, TestCaseTypeLkp, TestCaseStatusLkp
from app.infrastructure.models.portfolio_model import Portfolio  # portfolio_id, is_deleted
from app.infrastructure.models.program_model import Program  # program_id, portfolio_id, is_deleted
from app.infrastructure.models.project_model import Project  # project_id, program_id, is_deleted
from app.infrastructure.models.testcase_model import TestCase
from app.infrastructure.models.testcase_model import TestStep


class PortfolioAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------- helpers --------
    def _project_filter(self, portfolio_id: int, include_deleted: bool):
        filters = [Program.portfolio_id == portfolio_id]
        if not include_deleted:
            filters.extend([
                Portfolio.is_deleted.is_(False),
                Program.is_deleted.is_(False),
                Project.is_deleted.is_(False),
            ])
        return filters

    def _testcase_filter(self, portfolio_id: int, include_deleted: bool):
        filters = [Program.portfolio_id == portfolio_id, TestCase.project_id == Project.project_id]
        if not include_deleted:
            filters.extend([
                Portfolio.is_deleted.is_(False),
                Program.is_deleted.is_(False),
                Project.is_deleted.is_(False),
                TestCase.is_deleted.is_(False),
            ])
        return filters

    # -------- 2.1 Summary counts --------
    async def portfolio_summary(
            self, portfolio_id: int, include_deleted: bool = False
    ) -> Tuple[int, int, int, int, int]:
        # total programs, total projects (filtered by soft-delete if needed)
        prog_filters = [Program.portfolio_id == portfolio_id]
        proj_filters = [Program.id == portfolio_id, Project.program_id == Program.id]
        if not include_deleted:
            prog_filters.append(Program.is_deleted.is_(False))
            proj_filters.extend([Program.is_deleted.is_(False), Project.is_deleted.is_(False)])

        total_programs_stmt = select(func.count(func.distinct(Program.id))).where(*prog_filters)
        res_prog = await self.session.execute(total_programs_stmt)
        total_programs = int(res_prog.scalar_one() or 0)

        total_projects_stmt = (
            select(func.count(func.distinct(Project.project_id)))
            .join(Program, Program.id == Project.program_id)
            .where(*proj_filters)
        )
        res_proj = await self.session.execute(total_projects_stmt)
        total_projects = int(res_proj.scalar_one() or 0)

        # test case totals
        tc_filters = self._testcase_filter(portfolio_id, include_deleted)
        total_tc_stmt = (
            select(func.count(TestCase.id))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*tc_filters)
        )
        res_total = await self.session.execute(total_tc_stmt)
        total_test_cases = int(res_total.scalar_one() or 0)

        active_tc_stmt = (
            select(func.count(TestCase.id))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*self._testcase_filter(portfolio_id, include_deleted=False))  # active only
        )
        res_active = await self.session.execute(active_tc_stmt)
        active_test_cases = int(res_active.scalar_one() or 0)

        deleted_tc_stmt = (
            select(func.count(TestCase.id))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(Program.portfolio_id == portfolio_id, TestCase.is_deleted.is_(True))
        )
        res_deleted = await self.session.execute(deleted_tc_stmt)
        deleted_test_cases = int(res_deleted.scalar_one() or 0)

        return total_programs, total_projects, total_test_cases, active_test_cases, deleted_test_cases

    # -------- 2.2 Labeled breakdowns (priority/type/status) --------
    async def breakdown_priority(
            self, portfolio_id: int, include_deleted: bool = False, include_nulls: bool = False
    ) -> List[Tuple[int | None, str | None, int, int]]:
        base = (
            select(TestCase.priority_id, func.count(TestCase.id).label("cnt"))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*self._testcase_filter(portfolio_id, include_deleted))
            .group_by(TestCase.priority_id)
            .subquery()
        )
        stmt = (
            select(base.c.priority_id, PriorityLkp.display_name, PriorityLkp.sort_order, base.c.cnt)
            .join(PriorityLkp, PriorityLkp.id == base.c.priority_id, isouter=True)
            .order_by(PriorityLkp.sort_order.asc().nulls_last(), base.c.priority_id.asc().nulls_last())
        )
        if not include_nulls:
            stmt = stmt.where(base.c.priority_id.is_not(None))
        res = await self.session.execute(stmt)
        return [(i, lbl, int(cnt), int(sort) if sort is not None else 9999) for (i, lbl, cnt, sort) in res.all()]

    async def breakdown_type(
            self, portfolio_id: int, include_deleted: bool = False, include_nulls: bool = False
    ) -> List[Tuple[int | None, str | None, int, int]]:
        base = (
            select(TestCase.test_case_type_id, func.count(TestCase.id).label("cnt"))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*self._testcase_filter(portfolio_id, include_deleted))
            .group_by(TestCase.test_case_type_id)
            .subquery()
        )
        stmt = (
            select(base.c.test_case_type_id, TestCaseTypeLkp.display_name, TestCaseTypeLkp.sort_order, base.c.cnt)
            .join(TestCaseTypeLkp, TestCaseTypeLkp.id == base.c.test_case_type_id, isouter=True)
            .order_by(TestCaseTypeLkp.sort_order.asc().nulls_last(), base.c.test_case_type_id.asc().nulls_last())
        )
        if not include_nulls:
            stmt = stmt.where(base.c.test_case_type_id.is_not(None))
        res = await self.session.execute(stmt)
        return [(i, lbl, int(cnt), int(sort) if sort is not None else 9999) for (i, lbl, cnt, sort) in res.all()]

    async def breakdown_status(
            self, portfolio_id: int, include_deleted: bool = False, include_nulls: bool = False
    ) -> List[Tuple[int | None, str | None, int, int]]:
        base = (
            select(TestCase.test_case_status_id, func.count(TestCase.id).label("cnt"))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*self._testcase_filter(portfolio_id, include_deleted))
            .group_by(TestCase.test_case_status_id)
            .subquery()
        )
        stmt = (
            select(base.c.test_case_status_id, TestCaseStatusLkp.display_name, TestCaseStatusLkp.sort_order, base.c.cnt)
            .join(TestCaseStatusLkp, TestCaseStatusLkp.id == base.c.test_case_status_id, isouter=True)
            .order_by(TestCaseStatusLkp.sort_order.asc().nulls_last(), base.c.test_case_status_id.asc().nulls_last())
        )
        if not include_nulls:
            stmt = stmt.where(base.c.test_case_status_id.is_not(None))
        res = await self.session.execute(stmt)
        return [(i, lbl, int(cnt), int(sort) if sort is not None else 9999) for (i, lbl, cnt, sort) in res.all()]

    # -------- 2.3 Cases without steps (count + light list) --------
    async def cases_without_steps(
            self, portfolio_id: int, include_deleted: bool = False, limit: int = 50
    ) -> Tuple[int, List[Tuple[int, int, str | None, datetime | None]]]:
        filters = self._testcase_filter(portfolio_id, include_deleted)
        # Anti-join: zero-step cases
        base = (
            select(
                TestCase.id.label("tc_id"),
                TestCase.project_id,
                TestCase.name,
                TestCase.created_at,
            )
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .join(TestStep, TestStep.test_case_id == TestCase.id, isouter=True)
            .where(*filters, TestStep.id.is_(None))
        )
        cnt_stmt = select(func.count()).select_from(base.subquery())
        res_cnt = await self.session.execute(cnt_stmt)
        count = int(res_cnt.scalar_one() or 0)

        list_stmt = base.order_by(TestCase.created_at.asc()).limit(limit)
        res_list = await self.session.execute(list_stmt)
        rows = [(int(tc_id), int(pid), name, created) for (tc_id, pid, name, created) in res_list.all()]
        return count, rows

    # -------- 2.4 Trend of test case creation across portfolio --------
    async def test_case_trend(
            self, portfolio_id: int, include_deleted: bool = False, bucket: str = "day",
            start_date: date | None = None, end_date: date | None = None
    ) -> List[Tuple[date, int]]:
        trunc = func.date_trunc(bucket, TestCase.created_at).label("bucket_start")
        filters = self._testcase_filter(portfolio_id, include_deleted)
        if start_date is not None:
            filters.append(TestCase.created_at >= func.date_trunc("day", func.timestamp(start_date)))
        if end_date is not None:
            filters.append(
                TestCase.created_at < func.date_trunc("day", func.timestamp(end_date)) + func.interval("1 day"))

        stmt = (
            select(trunc, func.count(TestCase.id))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*filters)
            .group_by(trunc)
            .order_by(trunc.asc())
        )
        res = await self.session.execute(stmt)
        return [(dt.date(), int(cnt)) for (dt, cnt) in res.all()]

    # -------- 2.5 Top projects by test case count --------
    async def top_projects(
            self, portfolio_id: int, include_deleted: bool = False, limit: int = 10
    ) -> List[Tuple[int, str | None, int]]:
        filters = self._testcase_filter(portfolio_id, include_deleted)
        stmt = (
            select(Project.project_id, Project.name, func.count(TestCase.id).label("cnt"))
            .join(Project, Project.project_id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(*filters)
            .group_by(Project.project_id, Project.name)
            .order_by(func.count(TestCase.id).desc(), Project.project_id.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(int(pid), name, int(cnt)) for (pid, name, cnt) in res.all()]
