from datetime import date, datetime
from typing import List, Dict

from pydantic import BaseModel, Field


class LabeledCount(BaseModel):
    id: int | None
    label: str | None
    count: int
    sort_order: int


class PortfolioSummaryOut(BaseModel):
    portfolio_id: int
    include_deleted: bool = False
    total_programs: int
    total_projects: int
    total_test_cases: int
    active_test_cases: int
    deleted_test_cases: int


class PortfolioBreakdownOut(BaseModel):
    portfolio_id: int
    include_deleted: bool = False
    by_priority: List[LabeledCount] = Field(default_factory=list)
    by_type: List[LabeledCount] = Field(default_factory=list)
    by_status: List[LabeledCount] = Field(default_factory=list)


class PortfolioCasesWithoutStepsOut(BaseModel):
    portfolio_id: int
    include_deleted: bool = False
    count: int
    # Light listing for diagnostics
    items: List[Dict[str, int | str | datetime | None]] = Field(default_factory=list)
    # each item can include: {project_id, test_case_id, name, created_at}


class PortfolioTrendPointOut(BaseModel):
    bucket_start: date
    count: int


class PortfolioTrendOut(BaseModel):
    portfolio_id: int
    include_deleted: bool = False
    bucket: str = "day"  # day/week/month
    points: List[PortfolioTrendPointOut] = Field(default_factory=list)


class PortfolioTopProjectsOut(BaseModel):
    portfolio_id: int
    include_deleted: bool = False
    limit: int = 10
    items: List[Dict[str, int | str]] = Field(default_factory=list)
    # each: {project_id, project_name, test_case_count}


class PortfolioCategoryCounts(BaseModel):
    name: str
    countsByStatus: Dict[str, int] = Field(default_factory=dict)


class PortfolioCategoryProjectsByStatusOut(BaseModel):
    year: int
    statuses: List[str] = Field(default_factory=list)
    categories: List[PortfolioCategoryCounts] = Field(default_factory=list)
