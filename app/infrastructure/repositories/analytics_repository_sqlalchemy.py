from datetime import date, datetime
from typing import Dict, List, Optional, Literal, Tuple

from sqlalchemy import select, func, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.testcase_model import TestCase, TestStep


class ProjectAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def test_case_summary(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> Tuple[int, int, int, Dict[int, int]]:

        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        # total/active/deleted
        total_active_deleted_stmt = (
            select(
                func.count(TestCase.id).label("total"),
                func.sum(
                    case((TestCase.is_deleted.is_(False), 1), else_=0)
                ).label("active"),
                func.sum(
                    case((TestCase.is_deleted.is_(True), 1), else_=0)
                ).label("deleted"),
            )
            .where(*filters)
        )

        res = await self.session.execute(total_active_deleted_stmt)
        row = res.one()
        total = int(row.total or 0)
        active = int(row.active or 0)
        deleted = int(row.deleted or 0)

        # breakdown by status id
        status_filters = [TestCase.project_id == project_id]
        if not include_deleted:
            status_filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            status_filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            status_filters.append(TestCase.folder_id == folder_id)

        by_status_stmt = (
            select(TestCase.test_case_status_id, func.count(TestCase.id))
            .where(*status_filters)
            .group_by(TestCase.test_case_status_id)
        )
        res2 = await self.session.execute(by_status_stmt)
        by_status = {int(k): int(v) for k, v in res2.all()}

        return total, active, deleted, by_status

    async def test_step_summary(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> Tuple[int, float]:
        """
        Steps aggregate across test_steps, but filtered through test_cases (project and soft-delete)
        """
        # Join steps -> cases to filter by project and deletion
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        # Total steps
        total_steps_stmt = (
            select(func.count(TestStep.id))
            .join(TestCase, TestCase.id == TestStep.test_case_id)
            .where(*filters)
        )
        res = await self.session.execute(total_steps_stmt)
        total_steps = int(res.scalar_one() or 0)

        # Average steps per (filtered) test case
        # Compute steps per case, then avg
        steps_per_case_stmt = (
            select(TestStep.test_case_id, func.count(TestStep.id).label("steps_count"))
            .join(TestCase, TestCase.id == TestStep.test_case_id)
            .where(*filters)
            .group_by(TestStep.test_case_id)
            .subquery()
        )
        avg_steps_stmt = select(func.coalesce(func.avg(steps_per_case_stmt.c.steps_count), 0.0))
        res2 = await self.session.execute(avg_steps_stmt)
        avg_steps = float(res2.scalar_one() or 0.0)

        return total_steps, avg_steps

    async def test_case_trend(
            self,
            project_id: int,
            bucket: Literal["day", "week", "month"] = "day",
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> List[Tuple[date, int]]:
        """
        Uses Postgres date_trunc on timestamptz (created_at).
        """
        bucket_map = {
            "day": literal_column("'day'"),
            "week": literal_column("'week'"),
            "month": literal_column("'month'"),
        }
        trunc = func.date_trunc(bucket, TestCase.created_at).label("bucket_start")

        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)
        if start_date is not None:
            # inclusive from midnight of start_date (server tz)
            filters.append(TestCase.created_at >= func.date_trunc("day", func.timestamp(start_date)))
        if end_date is not None:
            # inclusive through end of end_date; compare < next day for safety
            filters.append(
                TestCase.created_at < func.date_trunc("day", func.timestamp(end_date)) + func.interval("1 day"))

        stmt = (
            select(trunc, func.count(TestCase.id).label("count"))
            .where(*filters)
            .group_by(trunc)
            .order_by(trunc.asc())
        )
        res = await self.session.execute(stmt)
        items = []
        for dt, cnt in res.all():
            # dt is datetime aligned to bucket; convert to date for the response
            items.append((dt.date(), int(cnt)))
        return items

    async def breakdown_by_priority(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            include_nulls: bool = False,
    ) -> Dict[int, int]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)
        if not include_nulls:
            filters.append(TestCase.priority_id.is_not(None))

        stmt = (
            select(TestCase.priority_id, func.count(TestCase.id))
            .where(*filters)
            .group_by(TestCase.priority_id)
        )
        res = await self.session.execute(stmt)
        return {int(k): int(v) for k, v in res.all()}

    async def breakdown_by_type(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            include_nulls: bool = False,
    ) -> Dict[int, int]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)
        if not include_nulls:
            filters.append(TestCase.test_case_type_id.is_not(None))

        stmt = (
            select(TestCase.test_case_type_id, func.count(TestCase.id))
            .where(*filters)
            .group_by(TestCase.test_case_type_id)
        )
        res = await self.session.execute(stmt)
        return {int(k): int(v) for k, v in res.all()}

        # ---------- CASES WITHOUT STEPS ----------

    async def cases_without_steps_count(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> int:
        """
        Anti-join (LEFT OUTER JOIN ... WHERE step.id IS NULL) to count cases with zero steps.
        This preserves filtering on project, deletion, release, folder.
        """
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        # LEFT OUTER JOIN and keep only rows where there is no matching step
        stmt = (
            select(func.count(TestCase.id))
            .join(TestStep, TestStep.test_case_id == TestCase.id, isouter=True)
            .where(*filters, TestStep.id.is_(None))
        )
        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def cases_without_steps_list(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            limit: int = 50,
    ) -> List[Tuple[int, Optional[str], Optional[datetime]]]:
        """
        Returns (id, name, created_at) for cases with zero steps, ordered by oldest first.
        """
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        stmt = (
            select(TestCase.id, TestCase.name, TestCase.created_at)
            .join(TestStep, TestStep.test_case_id == TestCase.id, isouter=True)
            .where(*filters, TestStep.id.is_(None))
            .order_by(TestCase.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(int(i), n, c) for (i, n, c) in res.all()]
