from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional
from datetime import datetime, date

class ProjectBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    ProjectTemplateId: Optional[int] = None
    ProjectGroupId: Optional[int] = None
    Name: str = Field(min_length=1, max_length=255)
    Description: Optional[str] = None
    Website: Optional[str] = None
    Active: Optional[bool] = True
    WorkingHours: Optional[int] = Field(default=None, ge=0)
    WorkingDays: Optional[int] = Field(default=None, ge=0, le=7)
    NonWorkingHours: Optional[int] = Field(default=None, ge=0)
    StartDate: Optional[date] = None
    EndDate: Optional[date] = None
    PercentComplete: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("Website")
    @classmethod
    def validate_website(cls, v):
        if v is None or v.strip() == "":
            return None
        # simple normalization; for strict, use HttpUrl type
        return v.strip()

    @field_validator("EndDate")
    @classmethod
    def validate_dates(cls, end, info):
        start = info.data.get("StartDate")
        if start and end and end < start:
            raise ValueError("EndDate cannot be earlier than StartDate.")
        return end

class ProjectCreate(ProjectBase):
    # CreationDate is set by the DB; Name is only required field in the request.
    pass

class ProjectUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ProjectTemplateId: Optional[int] = None
    ProjectGroupId: Optional[int] = None
    Name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    Description: Optional[str] = None
    Website: Optional[str] = None
    Active: Optional[bool] = None
    WorkingHours: Optional[int] = Field(default=None, ge=0)
    WorkingDays: Optional[int] = Field(default=None, ge=0, le=7)
    NonWorkingHours: Optional[int] = Field(default=None, ge=0)
    StartDate: Optional[date] = None
    EndDate: Optional[date] = None
    PercentComplete: Optional[int] = Field(default=None, ge=0, le=100)

class ProjectOut(ProjectBase):
    ProjectId: int
    CreationDate: datetime

class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ProjectId: int
    Name: str
    Active: bool
    PercentComplete: Optional[int] = None
