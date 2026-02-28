from datetime import datetime, date
from typing import Optional, Dict, List

from pydantic import EmailStr, Field

from .common import CamelModel, BaseModel


class WorksiteInfo(BaseModel):
    # example shape; adjust keys as you wish
    code: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    extra: Dict[str, object] = Field(default_factory=dict)


class UserBase(CamelModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr = Field(max_length=100)
    department: str
    role: str
    unit: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    gender: Optional[str] = None
    birthday: date | None = None
    rss_token: Optional[str] = None
    admin: bool = False  # default server-side too
    superuser: bool = False
    phone: Optional[str] = None
    site: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    primary_worksite_info: WorksiteInfo = Field(default_factory=WorksiteInfo)
    secondary_worksite_info: WorksiteInfo = Field(default_factory=WorksiteInfo)


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserOut(CamelModel):
    id: int
    username: str
    email: EmailStr
    role: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    created_at: datetime
    updated_at: datetime


class UserSummary(CamelModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    department: str
    role: str
    unit: str
    active: bool
    admin: bool
    superuser: bool
    approved: bool
    locked: bool
    is_deleted: bool


class UserUpdate(CamelModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    unit: Optional[str] = None
    active: Optional[bool] = None
    approved: Optional[bool] = None
    locked: Optional[bool] = None
    admin: Optional[bool] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    rss_token: Optional[str] = None
    phone: Optional[str] = None
    site: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    skills: Optional[List[str]] = None
    primary_worksite_info: Optional[WorksiteInfo] = None
    secondary_worksite_info: Optional[WorksiteInfo] = None


class UserDeleteResponse(CamelModel):
    message: str
    data: UserOut
