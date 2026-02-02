from datetime import date
from typing import Optional, Literal, List

from app.infrastructure.repositories.analytics_repository_sqlalchemy import ProjectAnalyticsRepository
from app.infrastructure.repositories.project_repository_sqlalchemy import SQLAlchemyProjectRepository
from app.presentation.schemas.analytics_schema import (
    TestCaseBreakdownOut,
    CasesWithoutStepsOut,
    CaseLiteOut,
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
