from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.infrastructure.repositories.lookup_repository_sqlalchemy import LookupRepository
from app.presentation.schemas.lookup_schema import LookupItemOut, LookupListOut

lookup_router = APIRouter(prefix="/lookups", tags=["lookups"])


def repo(session: AsyncSession) -> LookupRepository:
    return LookupRepository(session)


@lookup_router.get("/test-case-statuses", response_model=LookupListOut)
async def get_test_case_statuses(
        include_inactive: bool = Query(False),
        session: AsyncSession = Depends(get_session),
):
    rows = await repo(session).statuses(include_inactive)
    items = [LookupItemOut(id=i, display_name=n, color_hex=c, sort_order=s, is_active=a) for (i, n, c, s, a) in rows]
    return {"items": items}


@lookup_router.get("/priorities", response_model=LookupListOut)
async def get_priorities(
        include_inactive: bool = Query(False),
        session: AsyncSession = Depends(get_session),
):
    rows = await repo(session).priorities(include_inactive)
    items = [LookupItemOut(id=i, display_name=n, color_hex=c, sort_order=s, is_active=a) for (i, n, c, s, a) in rows]
    return {"items": items}


@lookup_router.get("/test-case-types", response_model=LookupListOut)
async def get_test_case_types(
        include_inactive: bool = Query(False),
        session: AsyncSession = Depends(get_session),
):
    rows = await repo(session).case_types(include_inactive)
    items = [LookupItemOut(id=i, display_name=n, color_hex=c, sort_order=s, is_active=a) for (i, n, c, s, a) in rows]
    return {"items": items}
