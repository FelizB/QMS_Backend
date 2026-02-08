from typing import List, Optional

from pydantic import BaseModel, Field


class KeyCount(BaseModel):
    id: int
    name: Optional[str] = None
    count: int


class TestCaseSummaryOut(BaseModel):
    by_status: List[KeyCount]
    by_type: List[KeyCount]
    by_priority: List[KeyCount]
    total: int


class StepStatusCount(BaseModel):
    status_id: int
    status_name: Optional[str] = None
    count: int


class TestCaseStepSummaryItem(BaseModel):
    test_case_id: int
    test_case_name: str
    step_counts: List[StepStatusCount]
    total_steps: int


class TestStepsExecutionSummaryOut(BaseModel):
    items: List[TestCaseStepSummaryItem]


class TrendPoint(BaseModel):
    period: str
    count: int


class TestCaseTrendsOut(BaseModel):
    period: str
    series: List[TrendPoint]
    total: int


class TestCaseAgingOut(BaseModel):
    never_executed: int
    stale: int
    threshold_days: int


class LookupItem(BaseModel):
    id: int
    name: str
    display_name: Optional[str] = None
    color_hex: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class LookupListOut(BaseModel):
    items: List[LookupItem]


class MatrixCell(BaseModel):
    row_id: int  # status id
    row_name: Optional[str] = None
    col_id: int  # priority id
    col_name: Optional[str] = None
    count: int


class StatusPriorityMatrixOut(BaseModel):
    cells: List[MatrixCell]


class TopFailureItem(BaseModel):
    test_case_id: int
    test_case_name: str
    failed_steps: int
    total_steps: int


class TopFailuresOut(BaseModel):
    items: List[TopFailureItem]


class ReadinessBucket(BaseModel):
    bucket: str  # "NOT_STARTED" | "IN_PROGRESS" | "FULLY_EXECUTED"
    count: int


class ReadinessOut(BaseModel):
    buckets: List[ReadinessBucket]


class ReleaseCoverageOut(BaseModel):
    total_cases: int
    executed_cases: int
    not_executed_cases: int
    executed_pct: float


class CoverageOut(BaseModel):
    total_cases: int
    executed_cases: int
    not_executed_cases: int
    executed_pct: float


class FolderCount(BaseModel):
    folder_id: int
    count: int


class FolderBreakdownOut(BaseModel):
    items: List[FolderCount] = Field(default_factory=list)
    total: int


class TrendLinePoint(BaseModel):
    period: str  # ISO date, e.g., "2026-02-01"
    status_id: int
    status_name: Optional[str] = None
    count: int


class StepTrendOut(BaseModel):
    period: str  # "day" | "week" | "month"
    series: List[TrendLinePoint]
    total_steps: int


class KeyCount(BaseModel):
    id: int
    name: Optional[str] = None
    count: int


class TestCaseSummaryOut(BaseModel):
    by_status: List[KeyCount] = Field(default_factory=list)
    by_type: List[KeyCount] = Field(default_factory=list)
    by_priority: List[KeyCount] = Field(default_factory=list)
    total: int


class StepStatusCount(BaseModel):
    status_id: int
    status_name: Optional[str] = None
    count: int


class StepOverviewOut(BaseModel):
    totals: List[StepStatusCount] = Field(default_factory=list)
    total_steps: int
    pass_rate: Optional[float] = None


class HealthcardOut(BaseModel):
    summary: TestCaseSummaryOut
    steps_overview: StepOverviewOut
    coverage: CoverageOut
