from __future__ import annotations

from sqlalchemy import select, and_, desc, func, literal
from datetime import datetime

from typing import Optional, Mapping, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.models.activity_log import ActivityLog
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
# app/infrastructure/repositories/activity_log_repository.py

from typing import Optional
from sqlalchemy import select, func, and_, desc, or_
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

    async def list_logs(
            self,
            org_id: int | None,
            q: str | None = None,
            entity_type: EntityType | None = None,
            action: ActivityAction | None = None,
            outcome: ActivityOutcome | None = None,
            actor_id: int | None = None,
            from_dt=None,
            to_dt=None,
            page: int = 1,
            page_size: int = 20,
    ):
        filters = []
        if org_id is not None:
            filters.append(ActivityLog.org_id == org_id)

        if entity_type is not None:
            filters.append(ActivityLog.entity_type == entity_type)
        if action is not None:
            filters.append(ActivityLog.action == action)
        if outcome is not None:
            filters.append(ActivityLog.outcome == outcome)
        if actor_id is not None:
            filters.append(ActivityLog.actor_id == actor_id)

        if from_dt is not None:
            filters.append(ActivityLog.created_at >= from_dt)
        if to_dt is not None:
            filters.append(ActivityLog.created_at <= to_dt)

        if q:
            # Search on title + actor_first_name + request_id
            like = f"%{q.strip()}%"
            filters.append(
                or_(
                    ActivityLog.title.ilike(like),
                    ActivityLog.actor_first_name.ilike(like),
                    ActivityLog.request_id.ilike(like),
                )
            )

        base = select(ActivityLog).where(and_(*filters)) if filters else select(ActivityLog)

        # total
        total_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(total_q)).scalar_one()

        # page
        offset = (page - 1) * page_size
        items_q = (
            base.order_by(desc(ActivityLog.created_at))
            .offset(offset)
            .limit(page_size)
        )

        rows = (await self.session.execute(items_q)).scalars().all()
        return rows, total

    async def get_by_id(self, log_id: int, org_id: int | None = None):
        q = select(ActivityLog).where(ActivityLog.id == log_id)
        if org_id is not None:
            q = q.where(ActivityLog.org_id == org_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        return row
