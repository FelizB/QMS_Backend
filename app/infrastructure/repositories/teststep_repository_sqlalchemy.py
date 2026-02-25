from typing import Optional, List, Iterable

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.lookup_model import TestStepStatusLkp as R_ExecutionStatus
from app.infrastructure.models.testcase_model import TestStep

DEFAULT_EXEC_STATUS_CODE = "NOT_RUN"


class TestStepRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_case(self, test_case_id: int) -> List[TestStep]:
        stmt = select(TestStep).where(TestStep.test_case_id == test_case_id).order_by(TestStep.sequence.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get(self, step_id: int) -> Optional[TestStep]:
        return await self.session.get(TestStep, step_id)

    async def _next_sequence(self, test_case_id: int) -> int:
        stmt = select(func.coalesce(func.max(TestStep.sequence), 0)).where(TestStep.test_case_id == test_case_id)
        res = await self.session.execute(stmt)
        max_seq = res.scalar_one()
        return int(max_seq) + 1

    async def _get_default_status_id(self) -> int:
        # Resolve default by code so it works across environments
        res = await self.session.execute(
            select(R_ExecutionStatus.id).where(R_ExecutionStatus.code == DEFAULT_EXEC_STATUS_CODE)
        )
        status_id = res.scalar_one_or_none()
        if status_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Default execution status '{DEFAULT_EXEC_STATUS_CODE}' not found. Seed your lookups."
            )
        return status_id

    async def create(self, payload) -> TestStep:
        # if missing, default
        status_id = payload.test_step_status_id
        if status_id is None:
            status_id = await self._get_default_status_id()

        # Validate the referenced status exists (defensive)
        valid = await self.session.scalar(
            select(R_ExecutionStatus.id).where(R_ExecutionStatus.id == status_id)
        )
        if valid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test_step_status_id={status_id}"
            )

        entity = TestStep(
            test_case_id=payload.test_case_id,
            sequence=payload.sequence,
            action=payload.action,
            expected_result=payload.expected_result,
            test_step_status_id=status_id,
        )
        self.session.add(entity)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        await self.session.refresh(entity)
        return entity

    async def bulk_create(self, steps: Iterable[dict]) -> List[TestStep]:
        created = []
        for data in steps:
            obj = TestStep(**data)
            self.session.add(obj)
            created.append(obj)
        await self.session.commit()
        for obj in created:
            await self.session.refresh(obj)
        return created

    async def update(self, step_id: int, **fields) -> Optional[TestStep]:
        obj = await self.get(step_id)
        if not obj:
            return None
        for k, v in fields.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, step_id: int) -> bool:
        obj = await self.get(step_id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.commit()
        return True

    async def reorder(self, test_case_id: int, items: List[dict]) -> List[TestStep]:
        """
        items: [{'id': <step_id>, 'sequence': <new_seq>}, ...] for the SAME test_case_id
        """
        # Validate all steps belong to test_case_id
        ids = [i["id"] for i in items]
        stmt = select(TestStep).where(TestStep.id.in_(ids))
        res = await self.session.execute(stmt)
        fetched = {s.id: s for s in res.scalars().all()}
        if len(fetched) != len(ids):
            missing = set(ids) - set(fetched.keys())
            raise ValueError(f"Some step ids not found: {missing}")

        # Ensure ownership
        for s in fetched.values():
            if s.test_case_id != test_case_id:
                raise ValueError(f"Step {s.id} does not belong to test_case {test_case_id}")

        # Apply new sequences
        for it in items:
            fetched[it["id"]].sequence = it["sequence"]

        await self.session.commit()
        # Return ordered list
        stmt2 = select(TestStep).where(TestStep.test_case_id == test_case_id).order_by(TestStep.sequence.asc())
        res2 = await self.session.execute(stmt2)
        return list(res2.scalars().all())
