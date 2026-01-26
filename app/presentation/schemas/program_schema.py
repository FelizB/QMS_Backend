from typing import Optional, Any, Dict
from uuid import UUID

from pydantic import Field

from .common import CamelModel


class ProgramBase(CamelModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    website: Optional[str] = None
    portfolio_id: int
    project_template_id: Optional[int] = None
    workspace_type_id: Optional[int] = None
    artifact_type_id: Optional[int] = None
    is_active: bool = True
    is_default: bool = False
    custom_properties: Optional[Dict[str, Any]] = {}


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(CamelModel):
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    portfolio_id: Optional[int] = None
    project_template_id: Optional[int] = None
    workspace_type_id: Optional[int] = None
    artifact_type_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    custom_properties: Optional[Dict[str, Any]] = None
    # Optimistic concurrency
    concurrency_guid: UUID


class ProgramOut(ProgramBase):
    id: int
    guid: UUID
    concurrency_guid: UUID
    last_updated_date: UUID
