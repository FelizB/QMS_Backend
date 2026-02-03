# app/schemas/analytics.py
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
