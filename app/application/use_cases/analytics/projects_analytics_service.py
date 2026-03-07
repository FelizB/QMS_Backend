from datetime import date
from typing import Optional, Literal, List

from app.infrastructure.repositories.analytics_repository_sqlalchemy import ProjectAnalyticsRepository
from app.infrastructure.repositories.project_repository_sqlalchemy import SQLAlchemyProjectRepository
from app.presentation.schemas.analytics_schema import TestCaseBreakdownLabeledOut, LabeledCount
from app.presentation.schemas.analytics_schema import (
    TestCaseBreakdownOut,
    CasesWithoutStepsOut,
    CaseLiteOut,
    AgingMetricsOut,
    LongestCasesOut,
    LongestCaseItemOut,
    ReleaseCoverageOut,
    ReleaseBucketOut,
    PriorityHealthOut,
    TestCaseBreakdownLabeledOut,
    ProjectStatusCountsOut,
    StatusCountItem

)
from app.presentation.schemas.analytics_schema import TestCaseSummaryOut, TestStepSummaryOut, TrendPointOut


class ProjectAnalyticsService:
    def __init__(self, repo: ProjectAnalyticsRepository, p_repo=SQLAlchemyProjectRepository):
        self.repo = repo

    async def get_test_case_summary(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> TestCaseSummaryOut:
        total, active, deleted, by_status = await self.repo.test_case_summary(
            project_id, include_deleted, release_id, folder_id
        )

        return TestCaseSummaryOut(
            project_id=project_id,
            total_test_cases=total,
            active_test_cases=active,
            deleted_test_cases=deleted,
            by_status_id=by_status,
        )

    async def get_test_step_summary(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> TestStepSummaryOut:
        total_steps, avg_steps = await self.repo.test_step_summary(
            project_id, include_deleted, release_id, folder_id
        )
        return TestStepSummaryOut(
            project_id=project_id,
            total_steps=total_steps,
            average_steps_per_case=avg_steps,
        )

    async def get_test_case_trend(
            self,
            project_id: int,
            bucket: Literal["day", "week", "month"] = "day",
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
    ) -> List[TrendPointOut]:
        tuples = await self.repo.test_case_trend(
            project_id, bucket, start_date, end_date, include_deleted, release_id, folder_id
        )
        return [TrendPointOut(bucket_start=d, count=c) for d, c in tuples]

    async def get_breakdowns(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            include_nulls: bool = False,
    ) -> TestCaseBreakdownOut:
        by_priority = await self.repo.breakdown_by_priority(
            project_id, include_deleted, release_id, folder_id, include_nulls
        )
        by_type = await self.repo.breakdown_by_type(
            project_id, include_deleted, release_id, folder_id, include_nulls
        )
        return TestCaseBreakdownOut(
            project_id=project_id,
            include_deleted=include_deleted,
            by_priority_id=by_priority,
            by_type_id=by_type,
        )

    async def get_cases_without_steps(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            include_ids: bool = False,
            limit: int = 50,
    ) -> CasesWithoutStepsOut:
        count = await self.repo.cases_without_steps_count(
            project_id, include_deleted, release_id, folder_id
        )
        items = []
        if include_ids and count > 0:
            rows = await self.repo.cases_without_steps_list(
                project_id, include_deleted, release_id, folder_id, limit
            )
            items = [CaseLiteOut(id=i, name=n, created_at=c) for (i, n, c) in rows]

        return CasesWithoutStepsOut(
            project_id=project_id,
            include_deleted=include_deleted,
            release_id=release_id,
            folder_id=folder_id,
            count=count,
            items=items,
        )

    async def get_aging_metrics(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            stale_days: int = 30,
    ) -> AgingMetricsOut:
        (c_avg, c_p50, c_p90, c_max, c_stale,
         u_avg, u_p50, u_p90, u_max, u_stale) = await self.repo.aging_metrics(
            project_id, include_deleted, release_id, folder_id, stale_days
        )
        return AgingMetricsOut(
            project_id=project_id,
            include_deleted=include_deleted,
            release_id=release_id,
            folder_id=folder_id,
            stale_days=stale_days,
            created_days_avg=c_avg,
            created_days_p50=c_p50,
            created_days_p90=c_p90,
            created_days_max=c_max,
            created_older_than_stale_count=c_stale,
            updated_days_avg=u_avg,
            updated_days_p50=u_p50,
            updated_days_p90=u_p90,
            updated_days_max=u_max,
            updated_older_than_stale_count=u_stale,
        )

    async def get_longest_cases(
            self,
            project_id: int,
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            limit: int = 20,
    ) -> LongestCasesOut:
        rows = await self.repo.longest_cases(project_id, include_deleted, release_id, folder_id, limit)
        items = [LongestCaseItemOut(id=i, name=n, steps_count=s, created_at=c) for (i, n, s, c) in rows]
        return LongestCasesOut(
            project_id=project_id,
            include_deleted=include_deleted,
            release_id=release_id,
            folder_id=folder_id,
            limit=limit,
            items=items,
        )

    async def get_release_coverage(
            self,
            project_id: int,
            include_deleted: bool = False,
    ) -> ReleaseCoverageOut:
        total, assigned, unassigned, buckets = await self.repo.release_coverage(project_id, include_deleted)
        return ReleaseCoverageOut(
            project_id=project_id,
            include_deleted=include_deleted,
            total_cases=total,
            assigned_cases=assigned,
            unassigned_cases=unassigned,
            buckets=[ReleaseBucketOut(release_id=rid, count=cnt) for (rid, cnt) in buckets],
        )

    async def get_priority_health(
            self,
            project_id: int,
            high_priority_ids: List[int],
            include_deleted: bool = False,
            release_id: Optional[int] = None,
            folder_id: Optional[int] = None,
            stale_days: int = 30,
    ) -> PriorityHealthOut:
        total_hp, zero_steps, stale_count = await self.repo.priority_health(
            project_id, high_priority_ids, include_deleted, release_id, folder_id, stale_days
        )
        return PriorityHealthOut(
            project_id=project_id,
            include_deleted=include_deleted,
            release_id=release_id,
            folder_id=folder_id,
            high_priority_ids=high_priority_ids,
            stale_days=stale_days,
            total_high_priority=total_hp,
            high_priority_without_steps=zero_steps,
            high_priority_older_than_stale_count=stale_count,
        )

    async def get_breakdowns_labeled(
            self, project_id: int, include_deleted: bool = False,
            release_id: int | None = None, folder_id: int | None = None,
            include_nulls: bool = False,
    ) -> TestCaseBreakdownLabeledOut:
        pr = await self.repo.breakdown_by_priority_with_labels(project_id, include_deleted, release_id, folder_id,
                                                               include_nulls)
        ty = await self.repo.breakdown_by_type_with_labels(project_id, include_deleted, release_id, folder_id,
                                                           include_nulls)
        pr_items = [LabeledCount(id=i, label=lbl, count=c, sort_order=so) for (i, lbl, c, so) in pr]
        ty_items = [LabeledCount(id=i, label=lbl, count=c, sort_order=so) for (i, lbl, c, so) in ty]
        return TestCaseBreakdownLabeledOut(
            project_id=project_id,
            include_deleted=include_deleted,
            by_priority=pr_items,
            by_type=ty_items
        )

    async def get_status_counts(self) -> ProjectStatusCountsOut:
        rows = await self.repo.counts_by_status()
        total = await self.repo.total_projects()
        items: List[StatusCountItem] = [
            StatusCountItem(status=status, count=count) for status, count in rows
        ]
        return ProjectStatusCountsOut(total=total, items=items)
