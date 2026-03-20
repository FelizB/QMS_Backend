from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable, Dict, Mapping, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.activity_log_repo_sqlalchemy import ActivityLogRepository
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome

SENSITIVE_KEYS = {
    "password", "new_password", "old_password", "confirm_password",
    "token", "access_token", "refresh_token", "authorization", "secret",
    "client_secret", "otp", "code",
}


def _safe_meta(obj: Any) -> Dict[str, Any]:
    """
    Produce a sanitized, JSON-serializable dict for meta.
    - Drop or mask sensitive keys.
    - Keep small footprint (no huge payloads).
    """

    def scrub(d: Mapping[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in d.items():
            lk = str(k).lower()
            if lk in SENSITIVE_KEYS:
                out[k] = "***"
                continue
            if isinstance(v, Mapping):
                out[k] = scrub(v)
            elif isinstance(v, (list, tuple)):
                out[k] = [("***" if str(x).lower() in SENSITIVE_KEYS else x) for x in v][:50]
            else:
                out[k] = v
        return out

    if isinstance(obj, Mapping):
        return scrub(obj)
    try:
        # fallback to object __dict__ if present
        return scrub({k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")})
    except Exception:
        return {}


def _request_fingerprint(request: Optional[Request]) -> Dict[str, Any]:
    if not request:
        return {}
    ip = request.headers.get("x-forwarded-for") or request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    rid = getattr(getattr(request, "state", None), "request_id", None) or request.headers.get("x-request-id")
    return {
        "method": request.method,
        "path": request.url.path,
        "ip": ip,
        "user_agent": ua,
        "request_id": rid,
    }


def _request_id(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    return getattr(getattr(request, "state", None), "request_id", None) or request.headers.get("x-request-id")


class AuditLogger:
    """
    Convenience helpers to write success/failure entries.
    """

    @staticmethod
    async def success(
            session: AsyncSession,
            *,
            org_id: Optional[int],
            entity_type: EntityType,
            entity_id: int,
            action: ActivityAction,
            title: str,
            actor_id: Optional[int],
            actor_first_name: Optional[str],
            meta: Optional[Mapping[str, Any]] = None,
            request: Optional[Request] = None,
    ) -> None:
        meta_merged = {**_request_fingerprint(request), **(_safe_meta(meta) if meta else {})}
        repo = ActivityLogRepository(session)
        await repo.add(
            org_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            title=title,
            actor_id=actor_id,
            actor_first_name=actor_first_name,
            meta=meta_merged,
            outcome=ActivityOutcome.success,
            request_id=_request_id(request),
        )

    @staticmethod
    async def failure(
            session: AsyncSession,
            *,
            org_id: Optional[int],
            entity_type: EntityType,
            entity_id: int,
            action: ActivityAction,
            title: str,
            actor_id: Optional[int],
            actor_first_name: Optional[str],
            error_type: str,
            error_message: str,
            meta: Optional[Mapping[str, Any]] = None,
            request: Optional[Request] = None,
    ) -> None:
        meta_merged = {**_request_fingerprint(request), **(_safe_meta(meta) if meta else {})}
        repo = ActivityLogRepository(session)
        await repo.add(
            org_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            title=title,
            actor_id=actor_id,
            actor_first_name=actor_first_name,
            meta=meta_merged,
            outcome=ActivityOutcome.failed,
            error_type=error_type[:200],
            error_message=error_message[:800],
            request_id=_request_id(request),
        )


class audit_span(AbstractAsyncContextManager):
    """
    Async context manager that logs success/failure around an operation.

    Usage:
      async with audit_span(session, request,
                            entity_type=EntityType.USER,
                            action=ActivityAction.LOGIN,
                            title="User login",
                            actor_id=lambda: user.id if user else None,
                            actor_name=lambda: user.first_name if user else None,
                            entity_id=lambda: user.id if user else 0,
                            org_id=lambda: getattr(user, 'org_id', None),
                            extra_meta=lambda: {"username": form.username}):
          ... do the work ...
    """

    def __init__(
            self,
            session: AsyncSession,
            request: Optional[Request],
            *,
            entity_type: EntityType,
            action: ActivityAction,
            title: str,
            entity_id: Callable[[], Optional[int]],
            actor_id: Callable[[], Optional[int]] = lambda: None,
            actor_name: Callable[[], Optional[str]] = lambda: None,
            org_id: Callable[[], Optional[int]] = lambda: None,
            extra_meta: Callable[[], Optional[Mapping[str, Any]]] = lambda: None,
    ):
        self.session = session
        self.request = request
        self.entity_type = entity_type
        self.action = action
        self.title = title
        self._entity_id_fn = entity_id
        self._actor_id_fn = actor_id
        self._actor_name_fn = actor_name
        self._org_id_fn = org_id
        self._meta_fn = extra_meta
        self._exc: Optional[BaseException] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._exc = exc
        ent_id = self._entity_id_fn() or 0
        actor_id = self._actor_id_fn()
        actor_name = self._actor_name_fn()
        org_id = self._org_id_fn()
        meta = self._meta_fn() or {}

        if exc:
            await AuditLogger.failure(
                self.session,
                org_id=org_id,
                entity_type=self.entity_type,
                entity_id=ent_id,
                action=self.action,
                title=self.title,
                actor_id=actor_id,
                actor_first_name=actor_name,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                meta=meta,
                request=self.request,
            )
            # do not suppress
            return False

        await AuditLogger.success(
            self.session,
            org_id=org_id,
            entity_type=self.entity_type,
            entity_id=ent_id,
            action=self.action,
            title=self.title,
            actor_id=actor_id,
            actor_first_name=actor_name,
            meta=meta,
            request=self.request,
        )
        # let outer layer commit
        return False
