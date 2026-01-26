from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID

from pydantic import Field

from .common import CamelModel


class PortfolioBase(CamelModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    website: Optional[str] = None
    workspace_type_id: Optional[int] = None
    artifact_type_id: Optional[int] = None
    is_active: bool = True
    is_default: bool = False
    custom_properties: Optional[Dict[str, Any]] = {}


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(CamelModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    website: Optional[str] = None
    workspace_type_id: Optional[int] = None
    artifact_type_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    custom_properties: Optional[Dict[str, Any]] = None
    # Optimistic concurrency
    concurrency_guid: UUID


class PortfolioOut(CamelModel):
    id: int
    name: str
    is_active: bool
    is_deleted: bool
    guid: UUID
    concurrency_guid: UUID
    last_updated_date: datetime


class PortfolioPagedResult(CamelModel):
    total: int
    items: List[PortfolioOut]
    page: int
    page_size: int


class PortfolioDeleteResponse(CamelModel):
    message: str
    data: PortfolioOut
