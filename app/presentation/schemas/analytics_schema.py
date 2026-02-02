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
