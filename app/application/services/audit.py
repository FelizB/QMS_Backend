from __future__ import annotations
from typing import Optional, Mapping, Any, Dict
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.activity_log_repo_sqlalchemy import ActivityLogRepository as ActivityLogRepository
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome

SENSITIVE = {
    "password", "token", "access_token", "refresh_token",
    "old_password", "new_password", "authorization",
    "otp", "code", "secret",
}


def _clean(meta: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not meta:
        return {}
    out = {}
    for k, v in meta.items():
        if k.lower() in SENSITIVE:
            out[k] = "***"
        else:
            out[k] = v
    return out


def _fp(request: Optional[Request]) -> Dict[str, Any]:
    if not request:
        return {}
    ip = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    ua = request.headers.get("user-agent")
    rid = (
            getattr(getattr(request, "state", None), "request_id", None)
            or request.headers.get("x-request-id")
    )
    return {
        "method": request.method,
        "path": request.url.path,
        "ip": ip,
        "user_agent": ua,
        "request_id": rid,
    }


async def audit(
        session: AsyncSession,
        request: Optional[Request],
        *,
        title: str,
        entity_type: EntityType,
        entity_id: int,
        action: ActivityAction,
        outcome: ActivityOutcome,
        actor_id: Optional[int] = None,
        actor_first_name: Optional[str] = None,
        meta: Optional[Mapping[str, Any]] = None,
        org_id: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
):
    repo = ActivityLogRepository(session)

    merged_meta = {
        **_fp(request),
        **_clean(meta),
    }

    await repo.add(
        org_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        title=title,
        actor_id=actor_id,
        actor_first_name=actor_first_name,
        meta=merged_meta,
        outcome=outcome,
        error_type=error_type,
        error_message=error_message,
        request_id=merged_meta.get("request_id"),
    )
