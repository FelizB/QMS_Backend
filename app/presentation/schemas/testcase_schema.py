from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class TestStepIn(BaseModel):
    id: Optional[int] = None
    sequence: int = Field(ge=1)
    action: str
    expected_result: Optional[str] = None
    deleted: Optional[bool] = False


class TestStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sequence: int
    action: str
    expected_result: Optional[str]


class TestCaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    testCaseStatusId: int
    testCaseTypeId: int
    priorityId: Optional[int] = None
    releaseId: Optional[int] = None
    folderId: Optional[int] = None


class TestCaseUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    testCaseStatusId: Optional[int] = None
    testCaseTypeId: Optional[int] = None
    priorityId: Optional[int] = None
    releaseId: Optional[int] = None
    folderId: Optional[int] = None
    steps: Optional[List[TestStepIn]] = None


class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    description: Optional[str]
    test_case_status_id: int
    test_case_type_id: int
    priority_id: Optional[int]
    release_id: Optional[int]
    folder_id: Optional[int]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    steps: List[TestStepOut] = []


class PagedResult(BaseModel):
    total: int
    items: List[TestCaseOut]
    page: int
    page_size: int
