from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence, Any
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.sql.elements import and_
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.functions import func

from app.infrastructure.models.activity_log import ActivityLog, EntityType, ActivityAction
from app.infrastructure.models.project_model import Project


class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recent(
            self,
            limit: int = 5,
            org_id: int | None = None,
    ) -> list[dict[str, Any]]:
        pk_col = getattr(Project, "id", None) or getattr(Project, "project_id")
        name_col = getattr(Project, "name", None) or getattr(Project, "project_name")
        created_col = getattr(Project, "created_at", None) or getattr(Project, "creation_date")
        status_col = getattr(Project, "status", None) or getattr(Project, "project_status")
        owner_name_col = getattr(Project, "owner_name", None) or getattr(Project, "project_owner_name", None)

        filters = []
        if hasattr(Project, "is_deleted"):
            filters.append(Project.is_deleted == False)
        if org_id is not None and hasattr(Project, "org_id"):
            filters.append(Project.org_id == org_id)

        sel = [
            pk_col.label("id"),
            name_col.label("name"),
            created_col.label("created_at"),
            status_col.label("status"),
        ]
        if owner_name_col is not None:
            sel.append(owner_name_col.label("owner_name"))

        q = (select(*sel).where(and_(*filters)) if filters else select(*sel)) \
            .order_by(desc(created_col)) \
            .limit(limit)

        rows = (await self.session.execute(q)).mappings().all()
        # Always return a list of dicts
        return [
            {
                "id": int(r["id"]),
                "name": r["name"],
                "created_at": r["created_at"],
                "status": r["status"],
                "owner_name": r.get("owner_name"),
            }
            for r in rows
        ]
