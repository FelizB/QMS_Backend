from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class WorksiteInfo(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    active: bool
    superuser: bool
    admin: bool
    approved: bool
    locked: bool
    department: Optional[str] = None
    role: Optional[str] = None
    unit: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    initials: str
    initials_colors: str
    gender: str
    birthday: date | None = None
    phone: Optional[str] = None
    site: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None

    skills: List[str] = Field(default_factory=list)
    primary_worksite_info: WorksiteInfo = Field(default_factory=WorksiteInfo)
    secondary_worksite_info: WorksiteInfo = Field(default_factory=WorksiteInfo)

    model_config = {"from_attributes": True}


class LogoutOut(BaseModel):
    code: str
    message: str
    details: str | None = None
