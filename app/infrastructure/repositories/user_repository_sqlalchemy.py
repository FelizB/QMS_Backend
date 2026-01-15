from typing import Optional, Sequence
from datetime import timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from app.application.interfaces.user_repository import IUserRepository
from app.infrastructure.models.user_model import User as UserModel
from app.infrastructure.repositories._utils import make_deleted_username, make_deleted_email

class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: int) -> Optional[UserModel]:
        return await self.session.get(UserModel, id_)

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.username == username)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, user: UserModel) -> UserModel:
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            # Let caller decide conflict response
            raise
        await self.session.refresh(user)
        return user

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[UserModel]:
        stmt = select(UserModel).offset(offset).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def update_fields(self, id_: int, fields: dict) -> Optional[UserModel]:
        if not fields:
            return await self.get_by_id(id_)
        stmt = (
            update(UserModel)
            .where(UserModel.id == id_)
            .values(**fields)
            .returning(UserModel.id)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            await self.session.rollback()
            return None
        await self.session.commit()
        # reload
        return await self.get_by_id(id_)

    async def delete_user_and_return(self, id: int):

        user= await self.get_by_id(id)
        if not user or user.is_deleted:
            return None

        user.is_deleted = True
        user.deleted_at = func.now()
        user.active = False
        user.email = make_deleted_email(user.email, 100)
        user.username = make_deleted_username(user.username, 50)

        await self.session.flush()
        await self.session.refresh(user)
        return user
