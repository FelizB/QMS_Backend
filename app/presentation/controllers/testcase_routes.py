from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.testcases.testcase_usecase import (
    CreateTestCase, UpdateTestCaseWithSteps, GetTestCaseById,
    SoftDeleteTestCase, MoveTestCase, CountTestCases, SearchTestCases
)
from app.core.db import get_session
from app.presentation.dependencies.current_user import CurrentUser as get_current_user  # your auth
from app.presentation.schemas.testcase_schema import (
    TestCaseCreate, TestCaseUpdate, TestCaseOut, PagedResult
)

test_router = APIRouter(prefix="/projects/{project_id}/test-cases", tags=["Test Cases"])


@test_router.post("", response_model=TestCaseOut, status_code=201)
async def create_test_case(
        project_id: int,
        payload: TestCaseCreate,
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = CreateTestCase(session)
    try:
        obj = await usecase(project_id, payload.model_dump())
        await session.commit()
        return obj
    except Exception as e:
        await session.rollback()
        # Handle unique violation gracefully
        raise HTTPException(status_code=409, detail=str(e))


@test_router.put("", response_model=TestCaseOut)
async def update_test_case(
        project_id: int,
        payload: TestCaseUpdate,
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = UpdateTestCaseWithSteps(session)
    obj = await usecase(project_id, payload.model_dump())
    if not obj:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Test case not found")
    await session.commit()
    return obj


@test_router.get("/{test_case_id}", response_model=TestCaseOut)
async def get_test_case(
        project_id: int,
        test_case_id: int,
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = GetTestCaseById(session)
    obj = await usecase(project_id, test_case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


@test_router.delete("/{test_case_id}", status_code=200)
async def delete_test_case(
        project_id: int,
        test_case_id: int,
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = SoftDeleteTestCase(session)
    ok = await usecase(project_id, test_case_id)
    if not ok:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Not found")
    await session.commit()
    return {"message": "Test case deleted successfully"}


@test_router.post("/{test_case_id}/move")
async def move_test_case(
        project_id: int,
        test_case_id: int,
        test_case_folder_id: int = Query(..., description="Destination folder"),
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = MoveTestCase(session)
    ok = await usecase(project_id, test_case_id, test_case_folder_id)
    if not ok:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Not found")
    await session.commit()
    return {"message": "Moved"}


@test_router.get("/count")
async def count_test_cases_get(
        project_id: int,
        release_id: Optional[int] = None,
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = CountTestCases(session)
    total = await usecase(project_id, release_id, None)
    return {"total": total}


@test_router.post("/count")
async def count_test_cases_post(
        project_id: int,
        release_id: Optional[int] = None,
        filters: dict = {},
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = CountTestCases(session)
    total = await usecase(project_id, release_id, filters or {})
    return {"total": total}


@test_router.post("/search", response_model=PagedResult)
async def search_test_cases(
        project_id: int,
        starting_row: int = 0,
        number_of_rows: int = 20,
        sort_field: str = "updated_at",
        sort_direction: str = "desc",
        release_id: Optional[int] = None,
        filters: dict = {},
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    usecase = SearchTestCases(session)
    total, items = await usecase(project_id, starting_row, number_of_rows, sort_field, sort_direction, release_id,
                                 filters or {})
    page = (starting_row // number_of_rows) + 1 if number_of_rows else 1
    return {"total": total, "items": items, "page": page, "page_size": number_of_rows}
