from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.teststeps.teststep_usecases import (
    CreateTestStepUseCase, UpdateTestStepUseCase, DeleteTestStepUseCase,
    ListTestStepsUseCase, ReorderTestStepsUseCase
)
from app.core.db import get_session
from app.infrastructure.repositories.test_case_repository_sqlalchemy import TestCaseRepository
from app.infrastructure.repositories.teststep_repository_sqlalchemy import TestStepRepository
from app.presentation.schemas.teststep_schema import (
    TestStepCreate, TestStepUpdate, TestStepOut, TestStepReorderIn
)

step_router = APIRouter(prefix="/teststeps", tags=["teststeps"])


def get_repos(session: AsyncSession = Depends(get_session)):
    return TestStepRepository(session), TestCaseRepository(session)


@step_router.post("", response_model=TestStepOut, status_code=status.HTTP_201_CREATED)
async def create_test_step(payload: TestStepCreate, repos=Depends(get_repos)):
    steps_repo, cases_repo = repos
    uc = CreateTestStepUseCase(steps_repo, cases_repo)
    return await uc.execute(payload)


@step_router.get("/by-case/{test_case_id}", response_model=list[TestStepOut])
async def list_test_steps(test_case_id: int, repos=Depends(get_repos)):
    steps_repo, cases_repo = repos
    uc = ListTestStepsUseCase(steps_repo, cases_repo)
    return await uc.execute(test_case_id)


@step_router.patch("/{step_id}", response_model=TestStepOut)
async def update_test_step(step_id: int, payload: TestStepUpdate, repos=Depends(get_repos)):
    steps_repo, _ = repos
    uc = UpdateTestStepUseCase(steps_repo)
    return await uc.execute(step_id, payload)


@step_router.delete("/{step_id}", response_description="Delete a test step by ID")
async def delete_test_step(step_id: int, repos=Depends(get_repos)):
    steps_repo, _ = repos
    uc = DeleteTestStepUseCase(steps_repo)
    await uc.execute(step_id)
    return f"Test step with id {step_id} was deleted Successfully"


@step_router.post("/reorder", response_model=list[TestStepOut])
async def reorder_test_steps(payload: TestStepReorderIn, repos=Depends(get_repos)):
    steps_repo, cases_repo = repos
    uc = ReorderTestStepsUseCase(steps_repo, cases_repo)
    return await uc.execute(payload)
