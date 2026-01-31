from typing import Optional, List, Iterable

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.testcase_model import TestStep


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

    async def create(self, test_case_id: int, action: str, expected_result: Optional[str] = None,
                     sequence: Optional[int] = None) -> TestStep:
        if sequence is None:
            sequence = await self._next_sequence(test_case_id)

        obj = TestStep(
            test_case_id=test_case_id,
            action=action,
            expected_result=expected_result,
            sequence=sequence,
        )
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

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
