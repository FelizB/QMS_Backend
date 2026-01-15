from typing import Optional, Any, Dict
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
    concurrency_guid: str

class PortfolioOut(PortfolioBase):
    id: int
    guid: str
    concurrency_guid: str
    last_updated_date: str
