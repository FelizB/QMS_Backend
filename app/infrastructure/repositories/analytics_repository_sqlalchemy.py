from datetime import date, datetime
from typing import Dict, List, Optional, Literal, Tuple

from sqlalchemy import select, func, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.lookup_model import PriorityLkp, TestCaseTypeLkp
from app.infrastructure.models.testcase_model import TestCase, TestStep

SECONDS_PER_DAY = 86400.0


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

    async def aging_metrics(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            stale_days: int = 30,
    ) -> Tuple[float, float, float, float, int, float, float, float, float, int]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        created_days = (func.extract("epoch", func.now() - TestCase.created_at) / SECONDS_PER_DAY)
        updated_days = (func.extract("epoch", func.now() - TestCase.updated_at) / SECONDS_PER_DAY)

        created_stmt = select(
            func.coalesce(func.avg(created_days), 0.0),
            func.coalesce(func.percentile_cont(0.5).within_group(created_days), 0.0),
            func.coalesce(func.percentile_cont(0.9).within_group(created_days), 0.0),
            func.coalesce(func.max(created_days), 0.0),
        ).where(*filters)

        updated_stmt = select(
            func.coalesce(func.avg(updated_days), 0.0),
            func.coalesce(func.percentile_cont(0.5).within_group(updated_days), 0.0),
            func.coalesce(func.percentile_cont(0.9).within_group(updated_days), 0.0),
            func.coalesce(func.max(updated_days), 0.0),
        ).where(*filters)

        res_c = await self.session.execute(created_stmt)
        c_avg, c_p50, c_p90, c_max = map(float, res_c.one())

        res_u = await self.session.execute(updated_stmt)
        u_avg, u_p50, u_p90, u_max = map(float, res_u.one())

        # Counts older than threshold
        created_stale_stmt = select(func.count(TestCase.id)).where(*filters, created_days > stale_days)
        updated_stale_stmt = select(func.count(TestCase.id)).where(*filters, updated_days > stale_days)

        res_cs = await self.session.execute(created_stale_stmt)
        created_stale = int(res_cs.scalar_one() or 0)

        res_us = await self.session.execute(updated_stale_stmt)
        updated_stale = int(res_us.scalar_one() or 0)

        return c_avg, c_p50, c_p90, c_max, created_stale, u_avg, u_p50, u_p90, u_max, updated_stale

    async def longest_cases(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            limit: int = 20,
    ) -> List[Tuple[int, Optional[str], int, Optional[datetime]]]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        # LEFT JOIN to include zero-step cases; they just won't be in the "longest" top-N unless ties.
        stmt = (
            select(
                TestCase.id,
                TestCase.name,
                func.coalesce(func.count(TestStep.id), 0).label("steps_count"),
                TestCase.created_at,
            )
            .join(TestStep, TestStep.test_case_id == TestCase.id, isouter=True)
            .where(*filters)
            .group_by(TestCase.id, TestCase.name, TestCase.created_at)
            .order_by(func.count(TestStep.id).desc(), TestCase.id.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(int(i), n, int(s), c) for (i, n, s, c) in res.all()]

        # ---------------------------
        # Release coverage
        # ---------------------------

    async def release_coverage(
            self,
            project_id: int,
            include_deleted: bool = False,
    ) -> Tuple[int, int, int, List[Tuple[Optional[int], int]]]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))

        total_stmt = select(func.count(TestCase.id)).where(*filters)
        res_total = await self.session.execute(total_stmt)
        total = int(res_total.scalar_one() or 0)

        assigned_stmt = select(func.count(TestCase.id)).where(*filters, TestCase.release_id.is_not(None))
        res_assigned = await self.session.execute(assigned_stmt)
        assigned = int(res_assigned.scalar_one() or 0)

        unassigned = total - assigned

        buckets_stmt = (
            select(TestCase.release_id, func.count(TestCase.id))
            .where(*filters)
            .group_by(TestCase.release_id)
            .order_by(TestCase.release_id.asc().nulls_last())
        )
        res_b = await self.session.execute(buckets_stmt)
        buckets = [(rid, int(cnt)) for (rid, cnt) in res_b.all()]

        return total, assigned, unassigned, buckets

        # ---------------------------
        # Priority health (high priority focus)
        # ---------------------------

    async def priority_health(
            self,
            project_id: int,
            high_priority_ids: List[int],
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            stale_days: int = 30,
    ) -> Tuple[int, int, int]:
        filters = [TestCase.project_id == project_id, TestCase.priority_id.in_(high_priority_ids)]
        if not include_deleted:
            filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None:
            filters.append(TestCase.release_id == release_id)
        if folder_id is not None:
            filters.append(TestCase.folder_id == folder_id)

        # Total high-priority
        total_hp_stmt = select(func.count(TestCase.id)).where(*filters)
        res_total = await self.session.execute(total_hp_stmt)
        total_hp = int(res_total.scalar_one() or 0)

        # High priority with zero steps (anti-join)
        zero_steps_stmt = (
            select(func.count(TestCase.id))
            .join(TestStep, TestStep.test_case_id == TestCase.id, isouter=True)
            .where(*filters, TestStep.id.is_(None))
        )
        res_zero = await self.session.execute(zero_steps_stmt)
        zero_steps = int(res_zero.scalar_one() or 0)

        # High priority older than stale_days since updated_at
        updated_days = (func.extract("epoch", func.now() - TestCase.updated_at) / SECONDS_PER_DAY)
        stale_stmt = select(func.count(TestCase.id)).where(*filters, updated_days > stale_days)
        res_stale = await self.session.execute(stale_stmt)
        stale_count = int(res_stale.scalar_one() or 0)

        return total_hp, zero_steps, stale_count

    async def breakdown_by_priority_with_labels(
            self, project_id: int, include_deleted: bool = False,
            release_id: int | None = None, folder_id: int | None = None,
            include_nulls: bool = False,
    ) -> list[tuple[int | None, str | None, int, int]]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted: filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None: filters.append(TestCase.release_id == release_id)
        if folder_id is not None: filters.append(TestCase.folder_id == folder_id)

        agg = (
            select(TestCase.priority_id, func.count(TestCase.id).label("cnt"))
            .where(*filters)
            .group_by(TestCase.priority_id)
            .subquery()
        )

        stmt = (
            select(
                agg.c.priority_id,
                PriorityLkp.display_name,
                PriorityLkp.sort_order,
                agg.c.cnt
            )
            .join(PriorityLkp, PriorityLkp.id == agg.c.priority_id, isouter=True)
        )
        if not include_nulls:
            stmt = stmt.where(agg.c.priority_id.is_not(None))
        stmt = stmt.order_by(PriorityLkp.sort_order.asc().nulls_last(), agg.c.priority_id.asc().nulls_last())

        res = await self.session.execute(stmt)
        return [
            (pid, name, int(cnt), int(sort) if sort is not None else 9999)
            for (pid, name, sort, cnt) in res.all()
        ]

    async def breakdown_by_type_with_labels(
            self, project_id: int, include_deleted: bool = False,
            release_id: int | None = None, folder_id: int | None = None,
            include_nulls: bool = False,
    ) -> list[tuple[int | None, str | None, int, int]]:
        filters = [TestCase.project_id == project_id]
        if not include_deleted: filters.append(TestCase.is_deleted.is_(False))
        if release_id is not None: filters.append(TestCase.release_id == release_id)
        if folder_id is not None: filters.append(TestCase.folder_id == folder_id)

        agg = (
            select(TestCase.test_case_type_id, func.count(TestCase.id).label("cnt"))
            .where(*filters)
            .group_by(TestCase.test_case_type_id)
            .subquery()
        )

        stmt = (
            select(
                agg.c.test_case_type_id,
                TestCaseTypeLkp.display_name,
                TestCaseTypeLkp.sort_order,
                agg.c.cnt
            )
            .join(TestCaseTypeLkp, TestCaseTypeLkp.id == agg.c.test_case_type_id, isouter=True)
        )
        if not include_nulls:
            stmt = stmt.where(agg.c.test_case_type_id.is_not(None))
        stmt = stmt.order_by(TestCaseTypeLkp.sort_order.asc().nulls_last(), agg.c.test_case_type_id.asc().nulls_last())

        res = await self.session.execute(stmt)
        return [(tid, name, int(cnt), int(sort) if sort is not None else 9999) for (tid, name, cnt, sort) in res.all()]
