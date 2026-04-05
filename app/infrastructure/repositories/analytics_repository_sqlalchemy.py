from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional, Literal, Tuple, Type, Any

from sqlalchemy import select, func, case, literal_column, false, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import and_

from app.infrastructure.models.lookup_model import PriorityLkp, TestCaseTypeLkp
from app.infrastructure.models.portfolio_model import Portfolio
from app.infrastructure.models.program_model import Program
from app.infrastructure.models.project_model import Project
from app.infrastructure.models.testcase_model import TestCase, TestStep

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, desc, and_, literal, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Any
from app.infrastructure.models.activity_log import ActivityLog, EntityType, ActivityAction

EXECUTED_STATUSES = {"PASSED", "FAILED", "BLOCKED", "SKIPPED"}  # TODO: align to your enums

SECONDS_PER_DAY = 86400.0


def _pick_col(model, *names: str):
    """Return first existing SQLAlchemy column attribute from model by name."""
    for n in names:
        if hasattr(model, n):
            return getattr(model, n)
    return None


def enum_pick(enum_cls, *names: str):
    for n in names:
        if hasattr(enum_cls, n):
            return getattr(enum_cls, n)
    available = [m.name for m in enum_cls]
    raise RuntimeError(
        f"{enum_cls.__name__} missing all of {names}. Available: {available}"
    )


class ProjectAnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _counts_by_month(
            self,
            model: Type,
            created_attr: str,
            start_date: date,
            end_date: date,
            include_deleted: bool,
    ) -> Dict[date, int]:
        """
        Return {first_of_month_date: count} for creations within [start_date, end_date).
        Uses Postgres date_trunc('month', created_at).
        """
        created_col = getattr(model, created_attr)

        filters = [
            created_col >= start_date,
            created_col < end_date,
        ]
        if hasattr(model, "is_deleted") and not include_deleted:
            filters.append(model.is_deleted == false())

        month_label = func.date_trunc("month", created_col).label("mth")

        stmt = (
            select(month_label, func.count().label("cnt"))
            .where(and_(*filters))
            .group_by(month_label)
            .order_by(month_label)
        )

        rows = (await self.session.execute(stmt)).all()
        # date_trunc returns a timestamp (e.g., 2026-01-01 00:00:00)
        out: Dict[date, int] = {}
        for r in rows:
            # r.mth is datetime; convert to date()
            out[r.mth.date()] = int(r.cnt)
        return out

    async def monthly_portfolio_creations(
            self, year: int, include_deleted: bool = False
    ) -> Dict[date, int]:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        # Adjust created column name if your model differs
        return await self._counts_by_month(Portfolio, "created_at", start, end, include_deleted)

    async def monthly_program_creations(
            self, year: int, include_deleted: bool = False
    ) -> Dict[date, int]:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        return await self._counts_by_month(Program, "created_at", start, end, include_deleted)

    async def monthly_project_creations(
            self, year: int, include_deleted: bool = False
    ) -> Dict[date, int]:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        # If your project table uses "creation_date" instead, change here:
        # return await self._counts_by_month(Project, "creation_date", start, end, include_deleted)
        return await self._counts_by_month(Project, "creation_date", start, end, include_deleted)

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

    async def counts_by_status(self) -> List[Tuple[Optional[str], int]]:
        """
        Returns list of (status, count), including NULL as a bucket if present.
        """
        stmt = (
            select(Project.status, func.count().label("cnt"))
            .group_by(Project.status)
            .order_by(Project.status)
        )
        rows = (await self.session.execute(stmt)).all()
        # rows is a list of Row objects with [status, cnt]
        return [(r[0], int(r[1])) for r in rows]

    async def total_projects(self) -> int:
        stmt = select(func.count()).select_from(Project)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_projects_monthly(self, year: int) -> List[Dict[str, Any]]:
        """
        Returns 12 rows for the given year with `created` and `active_of_created` counts.
        Assumes: projects.created_at timestamptz (or creation_date), is_active boolean, deleted_at nullable.
        """
        sql = text("""
            WITH months AS (
              SELECT generate_series(
                date_trunc('year', make_date(:year, 1, 1))::timestamptz,
                (date_trunc('year', make_date(:year, 1, 1))::timestamptz + interval '11 months'),
                interval '1 month'
              ) AS month_start
            )
            SELECT
              EXTRACT(MONTH FROM m.month_start)::int AS month,
              to_char(m.month_start, 'Mon')         AS month_label,
              COALESCE(
                COUNT(*) FILTER (
                  WHERE p.project_id IS NOT NULL
                ), 0
              ) AS created,
              COALESCE(
                COUNT(*) FILTER (
                  WHERE p.project_id IS NOT NULL AND p.is_active = TRUE
                ), 0
              ) AS active_of_created
            FROM months m
            LEFT JOIN projects p
              ON p.deleted_at IS NULL
             AND date_trunc('month', p.creation_date) = m.month_start
            GROUP BY m.month_start
            ORDER BY m.month_start;
        """)

        rows = (await self.session.execute(sql, {"year": year})).mappings().all()
        return [dict(r) for r in rows]

    async def get_top_projects(
            self,
            limit: int = 4,
            window_days: int = 7,
            org_id: int | None = None,
    ) -> list[dict[str, Any]]:

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=window_days)
        prev_start = window_start - timedelta(days=window_days)
        prev_end = window_start

        # ---- Resolve Project PK and name columns safely ----
        pk_col = getattr(Project, "id", None) or getattr(Project, "project_id", None)
        name_col = getattr(Project, "name", None) or getattr(Project, "project_name", None)

        if pk_col is None or name_col is None:
            raise RuntimeError(
                "Project model must have either (id or project_id) and (name or project_name)."
            )

        # ---- Project filters ----
        p_filters = []
        if hasattr(Project, "is_deleted"):
            p_filters.append(Project.is_deleted.is_(False))
        if org_id is not None and hasattr(Project, "org_id"):
            p_filters.append(Project.org_id == org_id)

        projects_q = (
            select(
                pk_col.label("project_id"),
                name_col.label("project_name"),
            )
            .where(and_(*p_filters)) if p_filters else
            select(
                pk_col.label("project_id"),
                name_col.label("project_name"),
            )
        ).subquery("p")

        # ---- Test case stats per project (total + executed) ----
        tc_filters = []
        if hasattr(TestCase, "is_deleted"):
            tc_filters.append(TestCase.is_deleted.is_(False))
        if org_id is not None and hasattr(TestCase, "org_id"):
            tc_filters.append(TestCase.org_id == org_id)

        tc_stats_q = (
            select(
                TestCase.project_id.label("project_id"),
                func.count().label("total"),
                func.sum(
                    case(
                        (TestCase.test_case_status.in_(list(EXECUTED_STATUSES)), 1),
                        else_=0,
                    )
                ).label("executed"),
            )
            .where(and_(*tc_filters)) if tc_filters else
            select(
                TestCase.project_id.label("project_id"),
                func.count().label("total"),
                func.sum(
                    case(
                        (TestCase.test_case_status.in_(list(EXECUTED_STATUSES)), 1),
                        else_=0,
                    )
                ).label("executed"),
            )
        ).group_by(TestCase.project_id).subquery("tc_stats")

        # ---- Updates in current window from ActivityLog (entity_type=PROJECT only) ----
        # Your EntityType enum supports PROJECT; no TESTCASE exists, so we don't use it.
        upd_filters = [
            ActivityLog.entity_type == EntityType.PROJECT,
            ActivityLog.action.in_([ActivityAction.CREATE, ActivityAction.UPDATE]),
            ActivityLog.created_at >= window_start,
        ]
        if org_id is not None and hasattr(ActivityLog, "org_id"):
            upd_filters.append(ActivityLog.org_id == org_id)

        upd_curr_q = (
            select(
                ActivityLog.entity_id.label("project_id"),
                func.count().label("updates_in_window"),
            )
            .where(and_(*upd_filters))
            .group_by(ActivityLog.entity_id)
            .subquery("upd_curr")
        )

        # ---- Execution increments derived from TestCase timestamps ----
        # Prefer real execution timestamp if available.
        exec_ts_col = _pick_col(
            TestCase,
            "executed_at",
            "last_executed_at",
            "executed_on",
            "last_run_at",
            "updated_at",  # fallback: may be less accurate
        )

        # If no usable timestamp exists, we set increments to 0 and trend becomes flat.
        if exec_ts_col is not None:
            exec_base_filters = [TestCase.test_case_status.in_(list(EXECUTED_STATUSES))]
            if hasattr(TestCase, "is_deleted"):
                exec_base_filters.append(TestCase.is_deleted.is_(False))
            if org_id is not None and hasattr(TestCase, "org_id"):
                exec_base_filters.append(TestCase.org_id == org_id)

            exec_curr_q = (
                select(
                    TestCase.project_id.label("project_id"),
                    func.count().label("exec_incr_curr"),
                )
                .where(
                    and_(
                        *exec_base_filters,
                        exec_ts_col >= window_start,
                    )
                )
                .group_by(TestCase.project_id)
                .subquery("exec_curr")
            )

            exec_prev_q = (
                select(
                    TestCase.project_id.label("project_id"),
                    func.count().label("exec_incr_prev"),
                )
                .where(
                    and_(
                        *exec_base_filters,
                        exec_ts_col >= prev_start,
                        exec_ts_col < prev_end,
                    )
                )
                .group_by(TestCase.project_id)
                .subquery("exec_prev")
            )
        else:
            exec_curr_q = (
                select(
                    projects_q.c.project_id.label("project_id"),
                    literal_column("0").label("exec_incr_curr"),
                )
            ).subquery("exec_curr")

            exec_prev_q = (
                select(
                    projects_q.c.project_id.label("project_id"),
                    literal_column("0").label("exec_incr_prev"),
                )
            ).subquery("exec_prev")

        # ---- Compose final query ----
        join_q = (
            select(
                projects_q.c.project_id,
                projects_q.c.project_name,
                func.coalesce(tc_stats_q.c.total, 0).label("testcases_total"),
                func.coalesce(tc_stats_q.c.executed, 0).label("testcases_executed"),
                func.coalesce(upd_curr_q.c.updates_in_window, 0).label("updates_in_window"),
                func.coalesce(exec_curr_q.c.exec_incr_curr, 0).label("exec_incr_curr"),
                func.coalesce(exec_prev_q.c.exec_incr_prev, 0).label("exec_incr_prev"),
            )
            .select_from(projects_q)
            .join(tc_stats_q, tc_stats_q.c.project_id == projects_q.c.project_id, isouter=True)
            .join(upd_curr_q, upd_curr_q.c.project_id == projects_q.c.project_id, isouter=True)
            .join(exec_curr_q, exec_curr_q.c.project_id == projects_q.c.project_id, isouter=True)
            .join(exec_prev_q, exec_prev_q.c.project_id == projects_q.c.project_id, isouter=True)
            .order_by(desc("updates_in_window"), desc("testcases_executed"))
            .limit(limit)
        )

        rows = (await self.session.execute(join_q)).mappings().all()

        # ---- Compute progress + trend ----
        result: list[dict[str, Any]] = []
        for r in rows:
            total = int(r["testcases_total"])
            executed = int(r["testcases_executed"])
            progress_now = (executed * 100.0 / total) if total > 0 else 0.0

            inc_curr = int(r["exec_incr_curr"])
            inc_prev = int(r["exec_incr_prev"])
            trend = "up" if inc_curr > inc_prev else "down" if inc_curr < inc_prev else "flat"

            result.append({
                "project_id": int(r["project_id"]),
                "project_name": r["project_name"],
                "testcases_total": total,
                "testcases_executed": executed,
                "progress_percent": round(progress_now, 1),
                "trend": trend,
                "updates_in_window": int(r["updates_in_window"]),
            })

        return result

    async def get_recent_creations(
            self,
            limit: int = 5,
            org_id: int | None = None,
    ) -> list[dict]:
        filters = [Project.is_deleted == False]
        if org_id is not None:
            filters.append(Project.org_id == org_id)

        q = (
            select(
                Project.project_id,
                Project.name,
                Project.project_owner_name,
                Project.creation_date,
                Project.status,
                # TODO: If you have relationship to owner user, join to get owner name.
                # For now, assume denormalized owner_name on project (or null).
                # If not present, join to users table and concat first/last names.
                Project.project_owner_name,  # <-- add this column in your model or replace with join
            )
            .where(and_(*filters))
            .order_by(desc(Project.creation_date))
            .limit(limit)
        )
        rows = (await self.session.execute(q)).mappings().all()
        return [
            {
                "id": int(r["project_id"]),
                "name": r["name"],
                "created_at": r["creation_date"],
                "status": r["status"],
                "owner_name": r.get("project_owner_name"),
            }
            for r in rows
        ]
