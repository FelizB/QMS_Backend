from typing import Optional, Dict, List

from sqlalchemy import select, func, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.lookup_model import (
    TestCaseStatusLkp,
    TestCaseTypeLkp,
    PriorityLkp,
)
from app.infrastructure.models.testcase_model import TestCase, TestStep

try:
    from app.infrastructure.models.lookup_model import ExecutionStatusLkp

    HAS_EXEC_STATUS = True
except Exception:
    ExecutionStatusLkp = None
    HAS_EXEC_STATUS = False


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------- Helpers --------

    async def _map_lookup(self, model, id_col="id", name_col="display_name") -> Dict[int, str]:
        """
        Load id -> name mapping using display_name if present, else name.
        """
        if model is None:
            return {}
        cands = []
        try:
            # attempt display_name
            stmt = select(getattr(model, id_col), getattr(model, name_col))
            res = await self.session.execute(stmt)
            return dict(res.all())
        except Exception:
            pass

        try:
            stmt = select(getattr(model, id_col), getattr(model, "name"))
            res = await self.session.execute(stmt)
            return dict(res.all())
        except Exception:
            return {}

    # -------- Summaries --------

    async def test_case_total(self, project_id: int, release_id: Optional[int]) -> int:
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        # Add release filter only if column exists on your TestCase
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        stmt = select(func.count()).select_from(TestCase).where(*conds)
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def test_case_counts_by_status(self, project_id: int, release_id: Optional[int]) -> List[dict]:
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        # Adjust field name if your model uses a different foreign key
        status_fk = getattr(TestCase, "test_case_status_id")
        stmt = select(status_fk, func.count().label("count")).where(*conds).group_by(status_fk)
        rows = (await self.session.execute(stmt)).all()
        names = await self._map_lookup(TestCaseStatusLkp)
        return [{"id": _id, "name": names.get(_id), "count": int(cnt)} for (_id, cnt) in rows]

    async def test_case_counts_by_type(self, project_id: int, release_id: Optional[int]) -> List[dict]:
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        type_fk = getattr(TestCase, "test_case_type_id")
        stmt = select(type_fk, func.count().label("count")).where(*conds).group_by(type_fk)
        rows = (await self.session.execute(stmt)).all()
        names = await self._map_lookup(TestCaseTypeLkp)
        return [{"id": _id, "name": names.get(_id), "count": int(cnt)} for (_id, cnt) in rows]

    async def test_case_counts_by_priority(self, project_id: int, release_id: Optional[int]) -> List[dict]:
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        prio_fk = getattr(TestCase, "priority_id")
        stmt = select(prio_fk, func.count().label("count")).where(*conds).group_by(prio_fk)
        rows = (await self.session.execute(stmt)).all()
        names = await self._map_lookup(PriorityLkp)
        return [{"id": _id, "name": names.get(_id), "count": int(cnt)} for (_id, cnt) in rows]

    async def step_execution_summary_per_case(self, project_id: int, release_id: Optional[int]) -> List[dict]:
        """
        Aggregate steps grouped by test_case and execution_status_id.
        If you have an 'ExecutionStatusLkp', names will be included; otherwise names are None.
        """
        conds = [
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestStep.is_deleted.is_(False),
            TestStep.test_case_id == TestCase.id,
        ]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        stmt = (
            select(
                TestCase.id.label("test_case_id"),
                TestCase.name.label("test_case_name"),
                TestStep.test_step_status_id,
                func.count().label("count"),
            )
            .where(*conds)
            .group_by(TestCase.id, TestCase.name, TestStep.test_step_status_id)
            .order_by(TestCase.id.asc())
        )
        rows = (await self.session.execute(stmt)).all()

        status_names = await self._map_lookup(ExecutionStatusLkp) if HAS_EXEC_STATUS else {}

        by_case = {}
        totals = {}
        for tc_id, tc_name, status_id, count in rows:
            item = by_case.setdefault(tc_id, {
                "test_case_id": tc_id,
                "test_case_name": tc_name,
                "step_counts": []
            })
            item["step_counts"].append({
                "status_id": status_id,
                "status_name": status_names.get(status_id),
                "count": int(count),
            })
            totals[tc_id] = totals.get(tc_id, 0) + int(count)

        return [
            {
                "test_case_id": tc_id,
                "test_case_name": data["test_case_name"],
                "step_counts": data["step_counts"],
                "total_steps": totals.get(tc_id, 0),
            }
            for tc_id, data in by_case.items()
        ]

    async def trends_created(self, project_id: int, period: str, date_from: Optional[str], date_to: Optional[str]):
        """
        period: 'day' | 'week' | 'month'
        date_from/date_to: ISO date or full timestamp strings (UTC).
        """
        date_trunc = {"day": "day", "week": "week", "month": "month"}[period]
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]

        if date_from:
            conds.append(TestCase.created_at >= literal_column(f"TIMESTAMP '{date_from}'"))
        if date_to:
            conds.append(TestCase.created_at < literal_column(f"TIMESTAMP '{date_to}'"))

        bucket = func.date_trunc(date_trunc, TestCase.created_at).label("bucket")
        stmt = select(bucket, func.count()).where(*conds).group_by(bucket).order_by(bucket.asc())
        rows = (await self.session.execute(stmt)).all()

        total_stmt = select(func.count()).select_from(TestCase).where(*conds)
        total = int((await self.session.execute(total_stmt)).scalar() or 0)

        series = []
        for dt, cnt in rows:
            # For day/week/month, dt is a timestamp; serialize as date ISO
            series.append({"period": dt.date().isoformat(), "count": int(cnt)})

        return series, total

    async def aging(self, project_id: int, days_without_update: int, not_run_id: Optional[int] = 0):
        """
        never_executed: no step has execution_status_id != NOT_RUN (or no steps exist)
        stale: TestCase.updated_at older than threshold
        """
        from datetime import datetime, timedelta, timezone
        threshold = datetime.now(timezone.utc) - timedelta(days=days_without_update)

        # total cases
        cond_cases = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        total_cases = int((await self.session.execute(
            select(func.count()).select_from(TestCase).where(*cond_cases)
        )).scalar() or 0)

        # cases with any executed step (execution_status_id != NOT_RUN and not null)
        any_exec_stmt = (
            select(func.count(func.distinct(TestCase.id)))
            .select_from(TestCase)
            .join(TestStep, TestStep.test_case_id == TestCase.id, isouter=True)
            .where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
                TestStep.is_deleted.is_(False),
                TestStep.test_step_status_id.is_not(None),
                TestStep.test_step_status_id != not_run_id,
            )
        )
        any_executed = int((await self.session.execute(any_exec_stmt)).scalar() or 0)
        never_executed = total_cases - any_executed

        stale = int((await self.session.execute(
            select(func.count()).select_from(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
                TestCase.updated_at < threshold,
            )
        )).scalar() or 0)

        return never_executed, stale
