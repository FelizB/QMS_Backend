from datetime import date, datetime
from typing import List, Dict

from pydantic import BaseModel, Field


class LabeledCount(BaseModel):
    id: int | None
    label: str | None
    count: int
    sort_order: int


class ProgramSummaryOut(BaseModel):
    program_id: int
    include_deleted: bool = False
    total_projects: int
    total_test_cases: int
    active_test_cases: int
    deleted_test_cases: int


class ProgramBreakdownOut(BaseModel):
    program_id: int
    include_deleted: bool = False
    by_priority: List[LabeledCount] = Field(default_factory=list)
    by_type: List[LabeledCount] = Field(default_factory=list)
    by_status: List[LabeledCount] = Field(default_factory=list)


class ProgramCasesWithoutStepsOut(BaseModel):
    program_id: int
    include_deleted: bool = False
    count: int
    # Light list for diagnostics: which project/case are missing steps
    items: List[Dict[str, int | str | datetime | None]] = Field(default_factory=list)
    # each: {"test_case_id": int, "project_id": int, "name": str|None, "created_at": datetime|None}


class ProgramTrendPointOut(BaseModel):
    bucket_start: date
    count: int


class ProgramTrendOut(BaseModel):
    program_id: int
    include_deleted: bool = False
    bucket: str = "day"  # day|week|month
    points: List[ProgramTrendPointOut] = Field(default_factory=list)


class ProgramTopProjectsOut(BaseModel):
    program_id: int
    include_deleted: bool = False
    limit: int = 10
    items: List[Dict[str, int | str]] = Field(default_factory=list)
    # each: {"project_id": int, "project_name": str|None, "test_case_count": int}
