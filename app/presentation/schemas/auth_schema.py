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


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    active: bool
    superuser: bool
    admin: bool
    approved: bool
    locked: bool
    department: str
    role: str
    unit: str
    first_name: str
    middle_name: str
    last_name: str


class LogoutOut(BaseModel):
    code: str
    message: str
    details: str | None = None
