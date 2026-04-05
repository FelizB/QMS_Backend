from datetime import datetime
from pydantic import BaseModel
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome


class ActivityLogOut(BaseModel):
    id: int
    org_id: int | None
    entity_type: EntityType
    entity_id: int
    action: ActivityAction
    title: str
    actor_id: int | None
    actor_first_name: str | None
    meta: dict | None
    created_at: datetime
    outcome: ActivityOutcome
    error_type: str | None
    error_message: str | None
    request_id: str | None

    class Config:
        from_attributes = True


class PagedActivityLogOut(BaseModel):
    items: list[ActivityLogOut]
    total: int
    page: int
    page_size: int
