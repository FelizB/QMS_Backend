from __future__ import annotations

from datetime import date
from typing import Type, Optional

from sqlalchemy import select, and_, func, false
from sqlalchemy.ext.asyncio import AsyncSession

# Import your ORM models (adjust paths)
from app.infrastructure.models.portfolio_model import Portfolio
from app.infrastructure.models.program_model import Program
from app.infrastructure.models.project_model import Project
from app.infrastructure.models.user_model import User  # whatever your user model is


class DashboardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- helpers ----------

    @staticmethod
    def _created_col(model: Type):
        """
        Tries to find a created timestamp column on the model.
        Adjust list if your column names differ.
        """
        for name in ("created_at", "creation_date", "created_on", "created"):
            if hasattr(model, name):
                return getattr(model, name)
        raise AttributeError(f"{model.__name__} must have a created timestamp column")

    @staticmethod
    def _active_predicate(model: Type):
        """
        Returns a SQLAlchemy boolean column for 'active' if present, else None.
        Supports 'is_active' or 'active'.
        """
        if hasattr(model, "is_active"):
            return getattr(model, "is_active") == True
        if hasattr(model, "active"):
            return getattr(model, "active") == True
        return None

    @staticmethod
    def _not_deleted_predicate(model: Type):
        """
        Returns predicate to exclude soft-deleted rows if model has 'is_deleted'.
        """
        if hasattr(model, "is_deleted"):
            return getattr(model, "is_deleted") == false()
        return None

    async def _count_active(self, model: Type) -> int:
        filters = []
        active_pred = self._active_predicate(model)
        if active_pred is not None:
            filters.append(active_pred)
        not_deleted = self._not_deleted_predicate(model)
        if not_deleted is not None:
            filters.append(not_deleted)

        stmt = select(func.count()).select_from(model)
        if filters:
            stmt = stmt.where(and_(*filters))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def _count_created_between(self, model: Type, start: date, end_exclusive: date) -> int:
        created_col = self._created_col(model)
        filters = [created_col >= start, created_col < end_exclusive]
        not_deleted = self._not_deleted_predicate(model)
        if not_deleted is not None:
            filters.append(not_deleted)
        stmt = select(func.count()).where(and_(*filters)).select_from(model)
        res = await self.session.execute(stmt)
        return int(res.scalar_one())

    # ---------- Public entity methods ----------

    async def total_active_portfolios(self) -> int:
        return await self._count_active(Portfolio)

    async def total_active_programs(self) -> int:
        return await self._count_active(Program)

    async def total_active_projects(self) -> int:
        return await self._count_active(Project)

    async def total_active_users(self) -> int:
        return await self._count_active(User)

    async def created_portfolios(self, start: date, end_exclusive: date) -> int:
        return await self._count_created_between(Portfolio, start, end_exclusive)

    async def created_programs(self, start: date, end_exclusive: date) -> int:
        return await self._count_created_between(Program, start, end_exclusive)

    async def created_projects(self, start: date, end_exclusive: date) -> int:
        return await self._count_created_between(Project, start, end_exclusive)

    async def created_users(self, start: date, end_exclusive: date) -> int:
        return await self._count_created_between(User, start, end_exclusive)
