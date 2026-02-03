from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.lookup_model import TestCaseStatusLkp, PriorityLkp, TestCaseTypeLkp


class LookupRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def statuses(self, include_inactive: bool = False) -> list[tuple[int, str, str | None, int, bool]]:
        stmt = select(
            TestCaseStatusLkp.id,
            TestCaseStatusLkp.display_name,
            TestCaseStatusLkp.color_hex,
            TestCaseStatusLkp.sort_order,
            TestCaseStatusLkp.is_active
        )
        if not include_inactive:
            stmt = stmt.where(TestCaseStatusLkp.is_active.is_(True))
        stmt = stmt.order_by(TestCaseStatusLkp.sort_order.asc(), TestCaseStatusLkp.id.asc())
        res = await self.session.execute(stmt)
        return [(i, name, color, sort, active) for (i, name, color, sort, active) in res.all()]

    async def priorities(self, include_inactive: bool = False) -> list[tuple[int, str, str | None, int, bool]]:
        stmt = select(
            PriorityLkp.id,
            PriorityLkp.display_name,
            PriorityLkp.color_hex,
            PriorityLkp.sort_order,
            PriorityLkp.is_active
        )
        if not include_inactive:
            stmt = stmt.where(PriorityLkp.is_active.is_(True))
        stmt = stmt.order_by(PriorityLkp.sort_order.asc(), PriorityLkp.id.asc())
        res = await self.session.execute(stmt)
        return [(i, name, color, sort, active) for (i, name, color, sort, active) in res.all()]

    async def case_types(self, include_inactive: bool = False) -> list[tuple[int, str, str | None, int, bool]]:
        stmt = select(
            TestCaseTypeLkp.id,
            TestCaseTypeLkp.display_name,
            TestCaseTypeLkp.color_hex,
            TestCaseTypeLkp.sort_order,
            TestCaseTypeLkp.is_active
        )
        if not include_inactive:
            stmt = stmt.where(TestCaseTypeLkp.is_active.is_(True))
        stmt = stmt.order_by(TestCaseTypeLkp.sort_order.asc(), TestCaseTypeLkp.id.asc())
        res = await self.session.execute(stmt)
        return [(i, name, color, sort, active) for (i, name, color, sort, active) in res.all()]
