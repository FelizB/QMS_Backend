from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.presentation.schemas.common import CamelModel


class ProjectBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    program_id: int = Field(...)
    project_template_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    environment: str = Field(min_length=1, max_length=255)
    project_owner_id: Optional[int] = None
    project_owner_name: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = True
    status: Optional[str] = "New"
    working_hours: Optional[int] = Field(default=None, ge=0)
    working_days: Optional[int] = Field(default=None, ge=0, le=7)
    non_working_hours: Optional[int] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    percent_complete: Optional[int] = Field(default=None, ge=0, le=100)
    updated_date: Optional[datetime] = Field(default=None, nullable=True)


@field_validator("website")
@classmethod
def validate_website(cls, v):
    if v is None or v.strip() == "":
        return None
    # simple normalization; for strict, use HttpUrl type
    return v.strip()


@field_validator("end_date")
@classmethod
def validate_dates(cls, end, info):
    start = info.data.get("start_date")
    if start and end and end < start:
        raise ValueError("EndDate cannot be earlier than StartDate.")
    return end


class ProjectCreate(ProjectBase):
    # CreationDate is set by the DB; Name is only required field in the request.
    pass


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_template_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    environment: Optional[str] = None
    website: Optional[str] = None
    project_owner_id: Optional[int] = None
    project_owner_name: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    working_hours: Optional[int] = Field(default=None, ge=0)
    working_days: Optional[int] = Field(default=None, ge=0, le=7)
    non_working_hours: Optional[int] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    percent_complete: Optional[int] = Field(default=None, ge=0, le=100)


class ProjectOut(ProjectBase):
    project_id: int
    creation_date: datetime


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: int
    environment: str
    name: str
    is_active: bool
    project_owner_id: Optional[int] = None
    project_owner_name: Optional[str] = None
    percent_complete: Optional[int] = None
    creation_date: datetime
    updated_date: datetime


class ProjectSummaryDelete(CamelModel):
    project_id: int
    name: str
    updated_date: datetime
    is_active: bool


class ProjectDeleteOut(BaseModel):
    message: str
    data: ProjectSummaryDelete
