# app/application/use_cases/teststeps.py
from typing import List

from fastapi import HTTPException

from app.infrastructure.repositories.test_case_repository_sqlalchemy import TestCaseRepository  # you likely have this
from app.infrastructure.repositories.teststep_repository_sqlalchemy import TestStepRepository
from app.presentation.schemas.teststep_schema import (
    TestStepCreate, TestStepUpdate, TestStepOut, TestStepReorderIn
)


class CreateTestStepUseCase:
    def __init__(self, steps_repo: TestStepRepository, cases_repo: TestCaseRepository):
        self.steps_repo = steps_repo
        self.cases_repo = cases_repo

    async def execute(self, payload: TestStepCreate) -> TestStepOut:
        # Validate test_case exists and not soft-deleted
        case = await self.cases_repo.get(payload.test_case_id)
        if not case or getattr(case, "is_deleted", False):
            raise HTTPException(status_code=404, detail=f"Test case {payload.test_case_id} not found")

        obj = await self.steps_repo.create(payload)
        return TestStepOut.model_validate(obj, from_attributes=True)


class UpdateTestStepUseCase:
    def __init__(self, steps_repo: TestStepRepository):
        self.steps_repo = steps_repo

    async def execute(self, step_id: int, payload: TestStepUpdate) -> TestStepOut:
        fields = payload.model_dump(exclude_unset=True)
        obj = await self.steps_repo.update(step_id, **fields)
        if not obj:
            raise HTTPException(status_code=404, detail="Test step not found")
        return TestStepOut.model_validate(obj, from_attributes=True)


class DeleteTestStepUseCase:
    def __init__(self, steps_repo: TestStepRepository):
        self.steps_repo = steps_repo

    async def execute(self, step_id: int) -> None:
        ok = await self.steps_repo.delete(step_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Test step not found")


class ListTestStepsUseCase:
    def __init__(self, steps_repo: TestStepRepository, cases_repo: TestCaseRepository):
        self.steps_repo = steps_repo
        self.cases_repo = cases_repo

    async def execute(self, test_case_id: int) -> List[TestStepOut]:
        case = await self.cases_repo.get(test_case_id)
        if not case or getattr(case, "is_deleted", False):
            raise HTTPException(status_code=404, detail=f"Test case {test_case_id} not found")
        steps = await self.steps_repo.list_by_case(test_case_id)
        return [TestStepOut.model_validate(s, from_attributes=True) for s in steps]


class ReorderTestStepsUseCase:
    def __init__(self, steps_repo: TestStepRepository, cases_repo: TestCaseRepository):
        self.steps_repo = steps_repo
        self.cases_repo = cases_repo

    async def execute(self, payload: TestStepReorderIn) -> List[TestStepOut]:
        case = await self.cases_repo.get(payload.test_case_id)
        if not case or getattr(case, "is_deleted", False):
            raise HTTPException(status_code=404, detail=f"Test case {payload.test_case_id} not found")

        # Normalize items to dicts
        items = [{"id": it.id, "sequence": it.sequence} for it in payload.steps]
        steps = await self.steps_repo.reorder(payload.test_case_id, items)
        return [TestStepOut.model_validate(s, from_attributes=True) for s in steps]
