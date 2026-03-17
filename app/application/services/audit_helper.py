# app/application/services/audit_logger.py# app/application/services/audit_logger.py sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker

from app.infrastructure.models.activity_log import ActivityLog
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
from typing import Optional


class AuditLogger:
    def __init__(self, session: AsyncSession, session_factory: async_sessionmaker[AsyncSession],
                 request_id: Optional[str] = None):
        self.session = session
        self.session_factory = session_factory
        self.request_id = request_id

    async def log_success(
            self,
            *,
            org_id: int | None,
            entity_type: EntityType,
            entity_id: int | None,
            action: ActivityAction,
            title: str,
            actor_id: int | None,
            actor_first_name: str | None,
            metadata: dict | None = None,
    ):
        self.session.add(ActivityLog(
            org_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id or 0,
            action=action,
            title=title,
            actor_id=actor_id,
            actor_first_name=actor_first_name,
            meta=metadata,
            outcome=ActivityOutcome.SUCCESS,
            request_id=self.request_id,
        ))
        # no commit here—caller controls commit

    async def log_failure_fallback(
            self,
            *,
            org_id: int | None,
            entity_type: EntityType,
            entity_id: int | None,
            action: ActivityAction,
            title: str,
            actor_id: int | None,
            actor_first_name: str | None,
            error: Exception,
            metadata: dict | None = None,
    ):
        async with self.session_factory() as s:
            s.add(ActivityLog(
                org_id=org_id,
                entity_type=entity_type,
                entity_id=entity_id or 0,
                action=action,
                title=title,
                actor_id=actor_id,
                actor_first_name=actor_first_name,
                meta=metadata,
                outcome=ActivityOutcome.FAILURE,
                error_type=type(error).__name__,
                error_message=str(error)[:790],
                request_id=self.request_id,
            ))
            await s.commit()
