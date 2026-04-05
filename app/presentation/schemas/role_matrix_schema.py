from pydantic import BaseModel
from typing import Optional


class RoleIn(BaseModel):
    name: str


class RoleOut(BaseModel):
    id: int
    name: str
    is_default: bool


class ActionIn(BaseModel):
    name: str


class ActionOut(BaseModel):
    id: int
    name: str
    is_default: bool


class GrantIn(BaseModel):
    role: str  # role name
    action: str  # action name
    entity_type: Optional[str] = None
    allow: bool = True


class GrantOut(BaseModel):
    role: str
    action: str
    entity_type: Optional[str] = None
    allow: bool
