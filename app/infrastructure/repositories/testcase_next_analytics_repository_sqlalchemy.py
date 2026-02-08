from typing import Optional, List, Dict, Tuple

from sqlalchemy import select, func, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

# Your lookup models (we’ll use display_name where available)
from app.infrastructure.models.lookup_model import (
    TestCaseStatusLkp,
    TestCaseTypeLkp,
    PriorityLkp,
)
# Your ORM models (adjust imports if needed)
from app.infrastructure.models.testcase_model import TestCase
from app.infrastructure.models.testcase_model import TestStep

# Optional execution status lookup for names (safe to skip if absent)
try:
    from app.infrastructure.models.lookup_model import ExecutionStatusLkp

    HAS_EXEC_STATUS = True
except Exception:
    ExecutionStatusLkp = None
    HAS_EXEC_STATUS = False


class AnalyticsNextRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _name_map(self, model, id_col="id", prefer="display_name") -> Dict[int, str]:
        if model is None:
            return {}
        # try preferred column, fallback to 'name'
        try:
            rows = (await self.session.execute(select(getattr(model, id_col), getattr(model, prefer)))).all()
            return dict(rows)
        except Exception:
            try:
                rows = (await self.session.execute(select(getattr(model, id_col), getattr(model, "name")))).all()
                return dict(rows)
            except Exception:
                return {}

    # ---------- Coverage ----------

    async def coverage(self, project_id: int, release_id: Optional[int], not_run_id: Optional[int]) -> Tuple[
        int, int, int]:
        """
        executed_cases: a case with at least one step that has execution_status_id != NOT_RUN and not null
        not_executed_cases: total - executed
        """
        # total
        conds_cases = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds_cases.append(TestCase.release_id == release_id)

        total_cases = int((await self.session.execute(
            select(func.count()).select_from(TestCase).where(*conds_cases)
        )).scalar() or 0)

        # executed
        conds_exec = [
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestStep.is_deleted.is_(False),
            TestStep.test_case_id == TestCase.id,
            TestStep.test_step_status_id.is_not(None),
        ]
        if not_run_id is not None:
            conds_exec.append(TestStep.test_step_status_id != not_run_id)
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds_exec.append(TestCase.release_id == release_id)

        executed_cases = int((await self.session.execute(
            select(func.count(func.distinct(TestCase.id))).where(*conds_exec)
        )).scalar() or 0)

        not_executed_cases = max(0, total_cases - executed_cases)
        return total_cases, executed_cases, not_executed_cases

    # ---------- Folder breakdown ----------

    async def folder_breakdown(self, project_id: int, release_id: Optional[int]) -> Tuple[List[Tuple[int, int]], int]:
        """
        Count cases by folder_id (returns (folder_id, count)). If folder_id is nullable, rows with null are excluded.
        """
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        # If your column is named differently (e.g., `test_case_folder_id`), change here:
        folder_col = getattr(TestCase, "folder_id", None)
        if folder_col is None:
            # No folder column; return empty
            return [], int((await self.session.execute(
                select(func.count()).select_from(TestCase).where(*conds)
            )).scalar() or 0)

        rows = (await self.session.execute(
            select(folder_col, func.count()).where(*conds, folder_col.is_not(None)).group_by(folder_col)
        )).all()
        total = int((await self.session.execute(
            select(func.count()).select_from(TestCase).where(*conds)
        )).scalar() or 0)
        return [(int(fid), int(cnt)) for fid, cnt in rows], total

    # ---------- Step execution trend ----------

    async def step_execution_trend(
            self,
            project_id: int,
            release_id: Optional[int],
            period: str,
            date_from: Optional[str],
            date_to: Optional[str],
    ) -> Tuple[List[Tuple], int, Dict[int, str]]:
        """
        Returns list of (bucket_ts, status_id, count) sorted by bucket asc and status_id asc
        """
        trunc = {"day": "day", "week": "week", "month": "month"}[period]

        conds = [
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestStep.is_deleted.is_(False),
            TestStep.test_case_id == TestCase.id,
        ]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)
        if date_from:
            conds.append(TestStep.updated_at >= literal_column(f"TIMESTAMP '{date_from}'"))
        if date_to:
            conds.append(TestStep.updated_at < literal_column(f"TIMESTAMP '{date_to}'"))

        bucket = func.date_trunc(trunc, TestStep.updated_at).label("bucket")
        stmt = (
            select(bucket, TestStep.test_step_status_id, func.count())
            .where(*conds)
            .group_by(bucket, TestStep.test_step_status_id)
            .order_by(bucket.asc(), TestStep.test_step_status_id.asc())
        )
        rows = (await self.session.execute(stmt)).all()

        # Compute total steps in window (for reference)
        total_steps = int((await self.session.execute(
            select(func.count()).where(*conds)
        )).scalar() or 0)

        status_names = await self._name_map(ExecutionStatusLkp) if HAS_EXEC_STATUS else {}
        return rows, total_steps, status_names

    # ---------- Summary helpers (reuse from earlier repo to build Healthcard) ----------

    async def test_case_total(self, project_id: int, release_id: Optional[int]) -> int:
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)
        res = await self.session.execute(select(func.count()).select_from(TestCase).where(*conds))
        return int(res.scalar() or 0)

    async def counts_by_fk(self, project_id: int, release_id: Optional[int], fk_name: str) -> List[Tuple[int, int]]:
        conds = [TestCase.project_id == project_id, TestCase.is_deleted.is_(False)]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)
        fk_col = getattr(TestCase, fk_name)
        rows = (await self.session.execute(
            select(fk_col, func.count()).where(*conds).group_by(fk_col)
        )).all()
        return [(int(_id), int(cnt)) for _id, cnt in rows]

    async def step_overview(self, project_id: int, release_id: Optional[int]) -> Tuple[
        List[Tuple[int, int]], int, Dict[int, str]]:
        conds = [
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
            TestStep.is_deleted.is_(False),
            TestStep.test_case_id == TestCase.id,
        ]
        if release_id is not None and hasattr(TestCase, "release_id"):
            conds.append(TestCase.release_id == release_id)

        rows = (await self.session.execute(
            select(TestStep.test_step_status_id, func.count()).where(*conds).group_by(TestStep.test_step_status_id)
        )).all()
        total_steps = sum(int(c or 0) for _, c in rows)
        status_names = await self._name_map(ExecutionStatusLkp) if HAS_EXEC_STATUS else {}
        return rows, total_steps, status_names

    async def lookup_names(self) -> Tuple[Dict[int, str], Dict[int, str], Dict[int, str]]:
        statuses = await self._name_map(TestCaseStatusLkp)
        types = await self._name_map(TestCaseTypeLkp)
        priorities = await self._name_map(PriorityLkp)
        return statuses, types, priorities
