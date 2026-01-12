from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    Username: str = Field(min_length=3, max_length=50)
    Email: EmailStr = Field(max_length=100)
    Department: str
    Unit: str
    FirstName: str
    MiddleName: str
    LastName: str
    RssToken: Optional[str] = None
    Admin:bool

class UserCreate(UserBase):
    Password: str = Field(min_length=8)

class UserOut(BaseModel):
    id: int
    Username: str
    Email: EmailStr
    created_at: datetime
    updated_at: datetime

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    Username: str
    Email: EmailStr
    created_at: datetime
    updated_at: datetime
    Department: str
    Unit: str
    Active: bool
    Admin: bool
    Approved: bool
    Locked: bool

class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Username: Optional[str] = None
    Email: Optional[EmailStr] = None
    Department: Optional[str] = None
    Unit: Optional[str] = None
    Active: Optional[bool] = None
    Approved: Optional[bool] = None
    Locked: Optional[bool] = None
    Admin:Optional[bool]=None
    FirstName: Optional[str] = None
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None
    RssToken: Optional[str] = None


class UserDeleteResponse(BaseModel):
    message: str
    data: UserOut
