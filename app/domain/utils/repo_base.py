from __future__ import annotations
from typing import Any, Dict, Iterable, Mapping, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.domain.utils.select import rows_to_dicts


class RepoBase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_mapped(self, stmt: Select) -> list[dict]:
        rows = (await self.session.execute(stmt)).mappings().all()
        return rows_to_dicts(rows)
