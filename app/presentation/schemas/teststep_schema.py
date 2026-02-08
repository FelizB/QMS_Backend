# app/presentation/schemas/teststep_schemas.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class TestStepBase(BaseModel):
    action: str = Field(..., description="What to do")
    expected_result: Optional[str] = Field(None, description="Expected outcome")


class TestStepCreate(TestStepBase):
    test_case_id: int
    test_step_status_id: int
    sequence: Optional[int] = Field(None, ge=1, description="If omitted, will be appended at the end")


class TestStepUpdate(BaseModel):
    action: Optional[str] = None
    expected_result: Optional[str] = None
    sequence: Optional[int] = Field(None, ge=1)


class TestStepOut(TestStepBase):
    id: int
    test_case_id: int
    sequence: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReorderItem(BaseModel):
    id: int
    sequence: int


class TestStepReorderIn(BaseModel):
    test_case_id: int
    steps: List[ReorderItem]  # [{id:1, sequence:1}, {id:3, sequence:2}, ...]
