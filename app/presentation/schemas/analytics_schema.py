# app/schemas/analytics.py
from datetime import date, datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field

from app.domain.enum import ActivityAction


class TestCaseSummaryOut(BaseModel):
    project_id: int
    total_test_cases: int
    active_test_cases: int
    deleted_test_cases: int
    by_status_id: Dict[int, int] = Field(default_factory=dict)  # {status_id: count}


class TestStepSummaryOut(BaseModel):
    project_id: int
    total_steps: int
    average_steps_per_case: float


class TrendPointOut(BaseModel):
    bucket_start: date
    count: int


class TestCaseBreakdownOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    by_priority_id: Dict[int, int] = Field(default_factory=dict)  # {priority_id: count}
    by_type_id: Dict[int, int] = Field(default_factory=dict)  # {test_case_type_id: count}


class CaseLiteOut(BaseModel):
    id: int
    name: Optional[str] = None
    created_at: Optional[datetime] = None


class CasesWithoutStepsOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    release_id: Optional[int] = None
    folder_id: Optional[int] = None
    count: int
    items: List[CaseLiteOut] = Field(default_factory=list)  # optional list of cases lacking steps


class AgingMetricsOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    release_id: Optional[int] = None
    folder_id: Optional[int] = None
    stale_days: int = 30

    created_days_avg: float
    created_days_p50: float
    created_days_p90: float
    created_days_max: float
    created_older_than_stale_count: int

    updated_days_avg: float
    updated_days_p50: float
    updated_days_p90: float
    updated_days_max: float
    updated_older_than_stale_count: int


class LongestCaseItemOut(BaseModel):
    id: int
    name: Optional[str] = None
    steps_count: int
    created_at: Optional[datetime] = None


class LongestCasesOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    release_id: Optional[int] = None
    folder_id: Optional[int] = None
    limit: int = 20
    items: List[LongestCaseItemOut] = Field(default_factory=list)


class ReleaseBucketOut(BaseModel):
    release_id: Optional[int]  # None means "unassigned"
    count: int


class ReleaseCoverageOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    total_cases: int
    assigned_cases: int
    unassigned_cases: int
    buckets: List[ReleaseBucketOut] = Field(default_factory=list)


class PriorityHealthOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    release_id: Optional[int] = None
    folder_id: Optional[int] = None
    high_priority_ids: List[int] = Field(default_factory=list)
    stale_days: int = 30

    total_high_priority: int
    high_priority_without_steps: int
    high_priority_older_than_stale_count: int


class LabeledCount(BaseModel):
    id: int | None
    label: str | None
    count: int
    sort_order: int


class TestCaseBreakdownLabeledOut(BaseModel):
    project_id: int
    include_deleted: bool = False
    by_priority: list[LabeledCount] = Field(default_factory=list)
    by_type: list[LabeledCount] = Field(default_factory=list)


class MonthlyCreationItem(BaseModel):
    month: str = Field(..., description="YYYY-MM (first day of month)")
    portfolios: int
    programs: int
    projects: int


class MonthlyCreationsOut(BaseModel):
    year: int
    items: List[MonthlyCreationItem]


class PeriodOut(BaseModel):
    current_month_start: date
    previous_month_start: date


class PeriodOut(BaseModel):
    current_month_start: date
    previous_month_start: date


Trend = Literal['up', 'down', 'flat']


class EntitySummaryOut(BaseModel):
    total_active: int = Field(..., description="Active rows total")
    current_month: int = Field(..., description="Creations this month")
    previous_month: int = Field(..., description="Creations last month")
    change_pct: Optional[float] = Field(
        None,
        description="Percent change vs previous month; None when prev==0 and curr>0"
    )
    trend: Trend = Field(..., description="Direction of change: up | down | flat")
    change_label: str = Field(
        ..., description='Display label e.g. "NEW", "+25.0%", "-100.0%", "0%"'
    )


class DashboardSummaryOut(BaseModel):
    as_of: datetime
    period: PeriodOut
    portfolios: EntitySummaryOut
    programs: EntitySummaryOut
    projects: EntitySummaryOut
    users: EntitySummaryOut


class StatusCountItem(BaseModel):
    status: Optional[str]  # in case some rows have NULL
    count: int


class ProjectStatusCountsOut(BaseModel):
    total: int
    items: List[StatusCountItem]


class ProjectsMonthlyItem(BaseModel):
    month: int = Field(..., ge=1, le=12)
    month_label: str
    created: int = Field(..., ge=0)
    active_of_created: int = Field(..., ge=0)


class ProjectsMonthlyOut(BaseModel):
    year: int
    items: List[ProjectsMonthlyItem]
    total_created: int
    total_active_of_created: int


class RecentFeedItem(BaseModel):
    title: str
    actor_first_name: Optional[str] = None
    performed_at: datetime = Field(..., description="UTC timestamp")
    entity_type: str
    action: ActivityAction
    entity_id: int


class RecentFeedsOut(BaseModel):
    items: list[RecentFeedItem]
    total: int


class TopProjectItem(BaseModel):
    project_id: int
    project_name: str
    testcases_total: int
    testcases_executed: int
    progress_percent: float
    trend: Literal["up", "down", "flat"]
    updates_in_window: int


class TopProjectsOut(BaseModel):
    items: list[TopProjectItem]
    total: int


class RecentProjectCreationItem(BaseModel):
    id: int
    owner_name: Optional[str] = None
    name: str
    created_at: datetime
    status: str


class RecentProjectCreationsOut(BaseModel):
    items: list[RecentProjectCreationItem]
    total: int
