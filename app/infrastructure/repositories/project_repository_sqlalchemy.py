from typing import Optional, Sequence, Mapping, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from app.infrastructure.models.project_model import Project
from app.application.interfaces.project_repository import IProjectRepository

class SQLAlchemyProjectRepository(IProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[Project]:
        stmt = select(Project).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, project_id: int) -> Optional[Project]:
        return await self.session.get(Project, project_id)

    async def create(self, data: Mapping[str, Any]) -> Project:
        obj = Project(**data)
        self.session.add(obj)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(obj)
        return obj

    async def update_partial(self, project_id: int, fields: Mapping[str, Any]) -> Optional[Project]:
        if not fields:
            return await self.get_by_id(project_id)
        stmt = (
            update(Project)
            .where(Project.ProjectId == project_id)
            .values(**fields)
            .returning(Project.ProjectId)
        )
        res = await self.session.execute(stmt)
        returned_id = res.scalar_one_or_none()
        if not returned_id:
            await self.session.rollback()
            return None
        await self.session.commit()
        return await self.get_by_id(project_id)

    async def delete(self, project_id: int) -> bool:
        stmt = delete(Project).where(Project.ProjectId == project_id).returning(Project.ProjectId)
        res = await self.session.execute(stmt)
        returned_id = res.scalar_one_or_none()
        if not returned_id:
            await self.session.rollback()
            return False
        await self.session.commit()
        return True

    # If you adopt soft delete later:
    async def soft_delete_and_return(self, project_id: int) -> Optional[Project]:
        obj = await self.session.get(Project, project_id)
        if not obj:
            return None
        obj.is_deleted = True
        obj.deleted_at = os.datetime.now(timezone.utc)
        await self.session.commit()
        return obj
