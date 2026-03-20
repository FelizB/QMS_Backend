from sqlalchemy import select, and_, desc, func, literal
from datetime import datetime

from typing import Optional, Mapping, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.models.activity_log import ActivityLog
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome


class ActivityLogRepository:
    """
    Thin repo for ActivityLog. No commit/rollback here;
    caller (route/use-case) owns transaction boundaries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
            self,
            *,
            org_id: Optional[int],
            entity_type: EntityType,
            entity_id: int,
            action: ActivityAction,
            title: str,
            actor_id: Optional[int],
            actor_first_name: Optional[str],
            meta: Optional[Mapping[str, Any]],
            outcome: ActivityOutcome,
            error_type: Optional[str] = None,
            error_message: Optional[str] = None,
            request_id: Optional[str] = None,
    ) -> ActivityLog:
        log = ActivityLog(
            org_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            title=title,
            actor_id=actor_id,
            actor_first_name=actor_first_name,
            meta=dict(meta) if meta else None,
            outcome=outcome,
            error_type=error_type,
            error_message=error_message,
            request_id=request_id,
        )
        self.session.add(log)
        # caller may commit; we still flush to get PK if needed
        await self.session.flush()
        return log

    async def get_recent(
            self,
            limit: int = 20,
            since: datetime | None = None,
            org_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Returns the most recent activity log rows as list[dict] + total count.
        Keys are labeled to match RecentFeedItem / RecentFeedsOut:
          - title, actor_first_name, performed_at, entity_type, action, entity_id
        (Optional) outcome, error_type, error_message can be included for richer UI.
        """
        filters = []
        if since is not None:
            filters.append(ActivityLog.created_at >= since)
        if org_id is not None and hasattr(ActivityLog, "org_id"):
            filters.append(ActivityLog.org_id == org_id)

        # Count query
        total_stmt = select(func.count(ActivityLog.id))
        if filters:
            total_stmt = total_stmt.where(and_(*filters))
        total = (await self.session.execute(total_stmt)).scalar_one()

        # Labeled select → RowMapping → dicts
        stmt = select(
            ActivityLog.title.label("title"),
            ActivityLog.actor_first_name.label("actor_first_name"),
            ActivityLog.created_at.label("performed_at"),
            ActivityLog.entity_type.label("entity_type"),
            ActivityLog.action.label("action"),
            ActivityLog.entity_id.label("entity_id"),
            # Uncomment if you want to surface outcome/errors in UI:
            # ActivityLog.outcome.label("outcome"),
            # ActivityLog.error_type.label("error_type"),
            # ActivityLog.error_message.label("error_message"),
        )
        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(desc(ActivityLog.created_at)).limit(limit)

        rows = (await self.session.execute(stmt)).mappings().all()
        items = [dict(r) for r in rows]

        return items, total
