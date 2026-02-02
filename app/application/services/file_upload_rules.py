from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.infrastructure.models import (portfolio_model as Portfolio, project_model as Project, program_model as Program)
from app.infrastructure.models.testcase_model import TestCase
from app.infrastructure.models.testcase_model import TestStep


class EntityDeletedError(HTTPException):
    def __init__(self, entity: str):
        super().__init__(status_code=HTTP_409_CONFLICT, detail=f"{entity} is deleted; operation not allowed.")


class RelationMismatchError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=HTTP_409_CONFLICT, detail=message)


class RulesService:
    """
    Centralized guardrail service for checking:
      - Existence vs soft-deleted state of entities;
      - Cross-entity hierarchical consistency;
      - “No writes under deleted ancestors” invariant.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------- Basic existence + soft-delete checks --------

    async def ensure_portfolio_active(self, portfolio_id: int) -> None:
        q = select(Portfolio.is_deleted).where(Portfolio.id == portfolio_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Portfolio not found")
        if row:
            raise EntityDeletedError("Portfolio")

    async def ensure_program_active(self, program_id: int) -> None:
        q = select(Program.is_deleted).where(Program.id == program_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Program not found")
        if row:
            raise EntityDeletedError("Program")

    async def ensure_project_active(self, project_id: int) -> None:
        q = select(Project.is_deleted).where(Project.id == project_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        if row:
            raise EntityDeletedError("Project")

    async def ensure_test_case_active(self, test_case_id: int) -> None:
        q = select(TestCase.is_deleted).where(TestCase.id == test_case_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Test case not found")
        if row:
            raise EntityDeletedError("Test case")

    async def ensure_test_step_active(self, test_step_id: int) -> None:
        q = select(TestStep.is_deleted).where(TestStep.id == test_step_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Test step not found")
        if row:
            raise EntityDeletedError("Test step")

    # -------- Hierarchy membership checks --------

    async def assert_program_belongs_to_portfolio(self, program_id: int, portfolio_id: int) -> None:
        q = select(Program.id).where(
            Program.id == program_id,
            Program.portfolio_id == portfolio_id,
        )
        if (await self.session.execute(q)).scalar_one_or_none() is None:
            raise RelationMismatchError("Program does not belong to the given portfolio")

    async def assert_project_belongs_to_program(self, project_id: int, program_id: int) -> None:
        q = select(Project.id).where(
            Project.id == project_id,
            Project.program_id == program_id,
        )
        if (await self.session.execute(q)).scalar_one_or_none() is None:
            raise RelationMismatchError("Project does not belong to the given program")

    async def assert_test_case_belongs_to_project(self, test_case_id: int, project_id: int) -> None:
        q = select(TestCase.id).where(
            TestCase.id == test_case_id,
            TestCase.project_id == project_id,
        )
        if (await self.session.execute(q)).scalar_one_or_none() is None:
            raise RelationMismatchError("Test case does not belong to the given project")

    async def assert_test_step_belongs_to_test_case(self, test_step_id: int, test_case_id: int) -> None:
        q = select(TestStep.id).where(
            TestStep.id == test_step_id,
            TestStep.test_case_id == test_case_id,
        )
        if (await self.session.execute(q)).scalar_one_or_none() is None:
            raise RelationMismatchError("Test step does not belong to the given test case")

    # -------- Deep ancestor checks (quick joins) --------

    async def ensure_project_chain_active(self, project_id: int) -> None:
        """
        Ensure project is active and its ancestors (program, portfolio) are active.
        """
        q = (
            select(
                Project.is_deleted.label("project_deleted"),
                Program.is_deleted.label("program_deleted"),
                Portfolio.is_deleted.label("portfolio_deleted"),
            )
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(Project.id == project_id)
        )
        row = (await self.session.execute(q)).one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
        if row.project_deleted:
            raise EntityDeletedError("Project")
        if row.program_deleted:
            raise EntityDeletedError("Program")
        if row.portfolio_deleted:
            raise EntityDeletedError("Portfolio")

    async def ensure_test_case_chain_active(self, test_case_id: int) -> None:
        """
        Ensure test case is active + its project/program/portfolio are active.
        """
        q = (
            select(
                TestCase.is_deleted.label("tc_deleted"),
                Project.is_deleted.label("project_deleted"),
                Program.is_deleted.label("program_deleted"),
                Portfolio.is_deleted.label("portfolio_deleted"),
            )
            .join(Project, Project.id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(TestCase.id == test_case_id)
        )
        row = (await self.session.execute(q)).one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Test case not found")
        if row.tc_deleted:
            raise EntityDeletedError("Test case")
        if row.project_deleted:
            raise EntityDeletedError("Project")
        if row.program_deleted:
            raise EntityDeletedError("Program")
        if row.portfolio_deleted:
            raise EntityDeletedError("Portfolio")

    async def ensure_test_step_chain_active(self, test_step_id: int) -> None:
        """
        Ensure test step is active + its test case / project / program / portfolio are active.
        """
        # Join step -> case -> project -> program -> portfolio
        q = (
            select(
                TestStep.is_deleted.label("step_deleted"),
                TestCase.is_deleted.label("tc_deleted"),
                Project.is_deleted.label("project_deleted"),
                Program.is_deleted.label("program_deleted"),
                Portfolio.is_deleted.label("portfolio_deleted"),
            )
            .join(TestCase, TestCase.id == TestStep.test_case_id)
            .join(Project, Project.id == TestCase.project_id)
            .join(Program, Program.id == Project.program_id)
            .join(Portfolio, Portfolio.id == Program.portfolio_id)
            .where(TestStep.id == test_step_id)
        )
        row = (await self.session.execute(q)).one_or_none()
        if row is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Test step not found")
        if row.step_deleted:
            raise EntityDeletedError("Test step")
        if row.tc_deleted:
            raise EntityDeletedError("Test case")
        if row.project_deleted:
            raise EntityDeletedError("Project")
        if row.program_deleted:
            raise EntityDeletedError("Program")
        if row.portfolio_deleted:
            raise EntityDeletedError("Portfolio")

    # -------- Composite helper for file attachments --------

    async def validate_attachment_targets(
            self,
            *,
            project_id: int,
            test_case_id: Optional[int] = None,
            test_step_id: Optional[int] = None,
    ) -> None:
        """
        Enforce:
          - Project exists and is active (and ancestors active).
          - If test_case_id provided: it exists, active, and belongs to project.
          - If test_step_id provided: it exists, active, and belongs to the test_case (if provided),
            otherwise ensure it belongs to a test_case that belongs to the project.
        """

        # Ensure project chain active
        await self.ensure_project_chain_active(project_id)

        # If a test case is provided, ensure consistency + active chain
        if test_case_id is not None:
            await self.ensure_test_case_chain_active(test_case_id)
            await self.assert_test_case_belongs_to_project(test_case_id, project_id)

        # If a test step is provided, ensure consistency + active chain
        if test_step_id is not None:
            await self.ensure_test_step_chain_active(test_step_id)

            if test_case_id is not None:
                # Must belong to the provided test_case
                await self.assert_test_step_belongs_to_test_case(test_step_id, test_case_id)
            else:
                # No test_case_id given; infer and verify it *ultimately* belongs to this project
                q = (
                    select(Project.id)
                    .join(TestCase, TestCase.project_id == Project.id)
                    .join(TestStep, TestStep.test_case_id == TestCase.id)
                    .where(
                        Project.id == project_id,
                        TestStep.id == test_step_id,
                    )
                )
                if (await self.session.execute(q)).scalar_one_or_none() is None:
                    raise RelationMismatchError("Test step does not belong to a test case under the given project")
