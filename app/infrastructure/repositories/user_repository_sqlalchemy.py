from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.application.interfaces.user_repository import IUserRepository
from app.infrastructure.models.user_model import User as UserModel  # SQLAlchemy model

class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: int) -> Optional[UserModel]:
        return await self.session.get(UserModel, id_)

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.Username == username)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.Email == email)
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

    async def delete_user_and_return(self, id_: int):
        obj = await self.session.get(UserModel, id_)
        if not obj:
            return None
        await self.session.delete(obj)
        await self.session.commit()
        # Optionally detach/clone if you don’t want a live instance
        return obj
