# app/infrastructure/repositories/file_attachment_repository.py
from datetime import datetime, timezone
from typing import Sequence, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.file_attachment_model import FileAttachment


class FileAttachmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, obj: FileAttachment) -> FileAttachment:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def list(
            self, project_id: int, test_case_id: int | None = None, test_step_id: int | None = None
    ) -> Sequence[FileAttachment]:
        conds = [FileAttachment.project_id == project_id, FileAttachment.is_deleted.is_(False)]
        if test_case_id is not None:
            conds.append(FileAttachment.test_case_id == test_case_id)
        if test_step_id is not None:
            conds.append(FileAttachment.test_step_id == test_step_id)
        stmt = select(FileAttachment).where(and_(*conds)).order_by(FileAttachment.created_at.desc())
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get(self, project_id: int, file_id: int) -> Optional[FileAttachment]:
        stmt = select(FileAttachment).where(
            FileAttachment.id == file_id,
            FileAttachment.project_id == project_id,
            FileAttachment.is_deleted.is_(False),
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def soft_delete(self, project_id: int, file_id: int) -> bool:
        obj = await self.get(project_id, file_id)
        if not obj:
            return False
        obj.is_deleted = True
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True
