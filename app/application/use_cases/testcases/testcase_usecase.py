from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.testcase_model import TestCase
from app.infrastructure.repositories.test_case_repository_sqlalchemy import TestCaseRepository


class CreateTestCase:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, data: dict) -> TestCase:
        # Additional domain rules can be enforced here
        return await self.repo.create(project_id, data)


class UpdateTestCaseWithSteps:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, payload: dict) -> Optional[TestCase]:
        return await self.repo.update_with_steps(project_id, payload)


class GetTestCaseById:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, test_case_id: int) -> Optional[TestCase]:
        return await self.repo.get_by_id(project_id, test_case_id)


class SoftDeleteTestCase:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, test_case_id: int) -> bool:
        return await self.repo.soft_delete(project_id, test_case_id)


class MoveTestCase:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, test_case_id: int, folder_id: int) -> bool:
        return await self.repo.move(project_id, test_case_id, folder_id)


class CountTestCases:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, release_id: Optional[int], filters: Optional[dict] = None) -> int:
        return await self.repo.count(project_id, release_id, filters)


class SearchTestCases:
    def __init__(self, session: AsyncSession):
        self.repo = TestCaseRepository(session)

    async def __call__(self, project_id: int, starting_row: int, number_of_rows: int,
                       sort_field: str, sort_direction: str, release_id: Optional[int], filters: dict):
        return await self.repo.search(project_id, starting_row, number_of_rows, sort_field, sort_direction, release_id,
                                      filters or {})
