from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from .common import CamelModel


class UserBase(CamelModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr = Field(max_length=100)
    department: str
    unit: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    rss_token: Optional[str] = None
    admin: bool = False  # default server-side too


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserOut(CamelModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime


class UserSummary(CamelModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    department: str
    unit: str
    active: bool
    admin: bool
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


class UserDeleteResponse(CamelModel):
    message: str
    data: UserOut
