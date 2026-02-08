from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

# Import the models you actually have.
# These try/except guards make the service safe even if some models don't exist yet.
try:
    from app.infrastructure.models.project_model import Project  # adjust path/module
except Exception:
    Project = None  # type: ignore

try:
    from app.infrastructure.models.testcase_model import TestCase  # adjust path/module
except Exception:
    TestCase = None  # type: ignore

try:
    from app.infrastructure.models.testcase_model import TestStep  # adjust path/module
except Exception:
    TestStep = None  # type: ignore


class RulesService:
    """
    Centralized guards for:
      - Existence vs soft-delete checks
      - Basic membership checks between entities
    No dependency on FastAPI routing; safe to use from any use case.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- Project ----------

    async def ensure_project_active(self, project_id: int) -> None:
        """
        Ensure the project exists and is not soft-deleted.
        """
        if Project is None:
            # If you haven't defined a Project ORM yet, skip (no-op)
            return

        stmt = select(Project.is_deleted).where(Project.project_id == project_id)
        flag = (await self.session.execute(stmt)).scalar_one_or_none()
        if flag is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        if flag:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Project is deleted; operation not allowed")

    async def ensure_project_chain_active(self, project_id: int) -> None:
        """
        Placeholder for a future 'chain' (program/portfolio) check.
        For now this only checks the project (extend later if you add ancestors).
        """
        await self.ensure_project_active(project_id)

    async def ensure_test_case_active(self, test_case_id: int) -> None:
        if TestCase is None:
            return
        stmt = select(TestCase.is_deleted).where(TestCase.id == test_case_id)
        flag = (await self.session.execute(stmt)).scalar_one_or_none()
        if flag is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Test case not found")
        if flag:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Test case is deleted; operation not allowed")

    async def assert_test_case_belongs_to_project(self, test_case_id: int, project_id: int) -> None:
        if TestCase is None:
            return
        stmt = select(TestCase.id).where(
            TestCase.id == test_case_id,
            TestCase.project_id == project_id,
            TestCase.is_deleted.is_(False),
        )
        ok = (await self.session.execute(stmt)).scalar_one_or_none()
        if ok is None:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Test case does not belong to the given project")

    # ---------- Test Step ----------

    async def ensure_test_step_active(self, test_step_id: int) -> None:
        if TestStep is None:
            return
        stmt = select(TestStep.is_deleted).where(TestStep.id == test_step_id)
        flag = (await self.session.execute(stmt)).scalar_one_or_none()
        if flag is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Test step not found")
        if flag:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Test step is deleted; operation not allowed")

    async def assert_test_step_belongs_to_test_case(self, test_step_id: int, test_case_id: int) -> None:
        if TestStep is None:
            return
        stmt = select(TestStep.id).where(
            TestStep.id == test_step_id,
            TestStep.test_case_id == test_case_id,
            TestStep.is_deleted.is_(False),
        )
        ok = (await self.session.execute(stmt)).scalar_one_or_none()
        if ok is None:
            raise HTTPException(status_code=HTTP_409_CONFLICT,
                                detail="Test step does not belong to the given test case")
