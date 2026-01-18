from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.functions import func

from app.application.interfaces.user_repository import IUserRepository
from app.core.db import get_session
from app.infrastructure.models.user_model import User as UserModel
from app.infrastructure.repositories._utils import make_deleted_username, make_deleted_email


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session: get_session()) -> None:
        self.session = session

    async def get_by_id(self, id_: int) -> Optional[UserModel]:
        stmt = (
            select(UserModel)
            .where(
                UserModel.id == id_,
                UserModel.is_deleted.is_(False)  # 👈 enforce not deleted
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.username == username, UserModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email, UserModel.is_deleted.is_(False))
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
        stmt = select(UserModel).where(UserModel.is_deleted.is_(False)).offset(offset).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def update_fields(self, id_: int, fields: dict) -> Optional[UserModel]:
        res = await self.session.execute(
            select(UserModel.email, UserModel.username)
            .where(UserModel.id == id_, UserModel.is_deleted.is_(False))
        )
        if not res.scalar_one_or_none():
            return None
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

    async def delete_user_and_return(self, id: int) -> Optional[UserModel]:

        # 1) Read current values to compute new unique/tombstoned ones
        res = await self.session.execute(
            select(UserModel.email, UserModel.username)
            .where(UserModel.id == id, UserModel.is_deleted.is_(False))
        )
        curr = res.first()
        if not curr:
            await self.session.rollback()
            return None

        new_email = make_deleted_email(curr.email, max_len=100)
        new_username = make_deleted_username(curr.username, max_len=50)

        # 2) UPDATE with a guard (not already deleted) + RETURNING id
        stmt = (
            update(UserModel)
            .where(UserModel.id == id, UserModel.is_deleted.is_(False))
            .values(
                is_deleted=True,
                deleted_at=func.now(),
                active=False,
                email=new_email,
                username=new_username,
                updated_at=func.now(),
            )
            .returning(UserModel)

        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            await self.session.rollback()
            return None

        # 3) Commit (so changes persist)
        await self.session.commit()

        # 4) Reload & return the fully populated entity
        return row
