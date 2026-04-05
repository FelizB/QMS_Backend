# app/presentation/controllers/audit_logs.py
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException

from app.presentation.schemas.activity_log_schema import PagedActivityLogOut, ActivityLogOut
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
from app.infrastructure.repositories.activity_log_repo_sqlalchemy import ActivityLogRepository

from app.core.db import get_session

audit_router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Logs"])


@audit_router.get("", response_model=PagedActivityLogOut)
async def list_audit_logs(
        org_id: int | None = Query(None),
        q: str | None = Query(None),
        entity_type: EntityType | None = Query(None),
        action: ActivityAction | None = Query(None),
        outcome: ActivityOutcome | None = Query(None),
        actor_id: int | None = Query(None),
        from_dt: datetime | None = Query(None),
        to_dt: datetime | None = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=5, le=200),
        session=Depends(get_session),
):
    repo = ActivityLogRepository(session)
    items, total = await repo.list_logs(
        org_id=org_id,
        q=q,
        entity_type=entity_type,
        action=action,
        outcome=outcome,
        actor_id=actor_id,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        page_size=page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@audit_router.get("/{log_id}", response_model=ActivityLogOut)
async def get_audit_log(
        log_id: int,
        org_id: int | None = Query(None),
        session=Depends(get_session),
):
    repo = ActivityLogRepository(session)
    row = await repo.get_by_id(log_id, org_id=org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return row
