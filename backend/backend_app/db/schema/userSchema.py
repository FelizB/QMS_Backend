from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    Username: str
    Email: str
    Department: str
    Unit: str
    FirstName: str
    MiddleName: str
    LastName: str
    RssToken: str

class UserCreate(UserBase):
    hashed_password: str

class UserOut(UserBase):
    id: int
    Admin: bool
    Active: bool
    Approved: bool
    Locked: bool
    created_at: datetime
    updated_at: datetime

class UserSummary(BaseModel):
    id: int
    Username: str
    Email: str
    created_at: datetime
    updated_at: datetime
    Department: str
    Unit: str
    Active: bool

class UserUpdate(BaseModel):
    Username: Optional[str] = None
    Email: Optional[str] = None
    Department: Optional[str] = None
    Unit: Optional[str] = None
    Active: Optional[bool] = None
    Approved: Optional[bool] = None
    Locked: Optional[bool] = None


class Config:
    orm_mode = True   # allows SQLAlchemy → Pydantic conversion