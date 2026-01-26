from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.models.testcase_model import TestCase, TestStep


class TestCaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _base_query(self):
        return (
            select(TestCase)
            .where(TestCase.is_deleted == False)
            .options(selectinload(TestCase.steps))
        )

    async def create(self, project_id: int, data: dict) -> TestCase:
        obj = TestCase(
            project_id=project_id,
            name=data["name"],
            description=data.get("description"),
            test_case_status_id=data["testCaseStatusId"],
            test_case_type_id=data["testCaseTypeId"],
            priority_id=data.get("priorityId"),
            release_id=data.get("releaseId"),
            folder_id=data.get("folderId"),
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, project_id: int, test_case_id: int) -> Optional[TestCase]:
        res = await self.session.execute(
            self._base_query().where(
                TestCase.project_id == project_id,
                TestCase.id == test_case_id,
            )
        )
        return res.scalar_one_or_none()

    async def soft_delete(self, project_id: int, test_case_id: int) -> bool:
        obj = await self.get_by_id(project_id, test_case_id)
        if not obj:
            return False
        obj.is_deleted = True
        obj.deleted_at = datetime.utcnow()
        await self.session.flush()
        return True

    async def upsert_steps(self, test_case: TestCase, steps_payload: List[dict]) -> None:
        # Map existing by id for quick access
        existing = {s.id: s for s in (test_case.steps or [])}
        for s in steps_payload:
            if s.get("deleted"):
                sid = s.get("id")
                if sid and sid in existing:
                    await self.session.delete(existing[sid])
                continue

            if s.get("id") and s["id"] in existing:
                step = existing[s["id"]]
                step.sequence = s["sequence"]
                step.action = s["action"]
                step.expected_result = s.get("expected_result")
            else:
                self.session.add(TestStep(
                    test_case_id=test_case.id,
                    sequence=s["sequence"],
                    action=s["action"],
                    expected_result=s.get("expected_result")
                ))

        # Ensure uniqueness of sequence inside the same test_case is enforced by DB constraint.
        await self.session.flush()
        # Reload with sorted steps
        await self.session.refresh(test_case)

    async def update_with_steps(self, project_id: int, payload: dict) -> Optional[TestCase]:
        obj = await self.get_by_id(project_id, payload["id"])
        if not obj:
            return None

        # Update fields if provided
        for in_key, model_key in [
            ("name", "name"),
            ("description", "description"),
            ("testCaseStatusId", "test_case_status_id"),
            ("testCaseTypeId", "test_case_type_id"),
            ("priorityId", "priority_id"),
            ("releaseId", "release_id"),
            ("folderId", "folder_id"),
        ]:
            if payload.get(in_key) is not None:
                setattr(obj, model_key, payload[in_key])

        if payload.get("steps") is not None:
            await self.upsert_steps(obj, payload["steps"])

        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def move(self, project_id: int, test_case_id: int, new_folder_id: int) -> bool:
        obj = await self.get_by_id(project_id, test_case_id)
        if not obj:
            return False
        obj.folder_id = new_folder_id
        await self.session.flush()
        return True

    async def count(self, project_id: int, release_id: Optional[int] = None, filters: Optional[dict] = None) -> int:
        stmt = select(func.count()).select_from(TestCase).where(
            TestCase.project_id == project_id, TestCase.is_deleted == False
        )
        if release_id is not None:
            stmt = stmt.where(TestCase.release_id == release_id)
        # Optional: apply filters here
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def search(
            self,
            project_id: int,
            starting_row: int,
            number_of_rows: int,
            sort_field: str,
            sort_direction: str,
            release_id: Optional[int],
            filters: dict
    ) -> Tuple[int, List[TestCase]]:
        base = self._base_query().where(TestCase.project_id == project_id)
        if release_id is not None:
            base = base.where(TestCase.release_id == release_id)

        # Example filters
        name_contains = filters.get("nameContains")
        if name_contains:
            base = base.where(TestCase.name.ilike(f"%{name_contains}%"))

        status_ids = filters.get("statusIds")
        if status_ids:
            base = base.where(TestCase.test_case_status_id.in_(status_ids))

        type_ids = filters.get("typeIds")
        if type_ids:
            base = base.where(TestCase.test_case_type_id.in_(type_ids))

        priority_ids = filters.get("priorityIds")
        if priority_ids:
            base = base.where(TestCase.priority_id.in_(priority_ids))

        folder_ids = filters.get("folderIds")
        if folder_ids:
            base = base.where(TestCase.folder_id.in_(folder_ids))

        # Sorting
        col_map = {
            "updated_at": TestCase.updated_at,
            "created_at": TestCase.created_at,
            "name": TestCase.name,
        }
        order_col = col_map.get(sort_field, TestCase.updated_at)
        if sort_direction.lower() == "desc":
            base = base.order_by(desc(order_col))
        else:
            base = base.order_by(order_col)

        # Total
        total_stmt = select(func.count()).select_from(
            select(TestCase.id).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted == False
            ).subquery()
        )
        res_total = await self.session.execute(total_stmt)
        total = int(res_total.scalar() or 0)

        # Page window
        base = base.offset(starting_row).limit(number_of_rows)
        res = await self.session.execute(base)
        items = list(res.scalars().unique())
        return total, items
