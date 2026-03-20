from datetime import datetime, timezone
from typing import Optional, Set, Sequence

from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.user_repository import IUserRepository
from app.infrastructure.models.role_matrix import RoleActionGrant, UserRole, Role
from app.infrastructure.models.user_model import User as UserModel
from app.infrastructure.repositories._utils import make_deleted_username, make_deleted_email


class SQLAlchemyUserRepository(IUserRepository):

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------
    # Reads
    # -----------------------
    async def get_by_id(self, id_: int) -> Optional[UserModel]:
        stmt = (
            select(UserModel)
            .where(
                UserModel.id == id_,
                UserModel.is_deleted.is_(False)
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        res = await self.session.execute(select(Role).where(Role.id == role_id).limit(1))
        role = res.scalar_one_or_none()
        return role

    async def get_role_permissions(self, role_id: int) -> Set[str]:
        """
    Returns
    effective
    permissions
    for a role as a set of strings.
    Adjust
    the
    projection if your
    column is named
    differently(e.g., permission_code).
    """
        res = await self.session.execute(
            select(RoleActionGrant.action_id).where(RoleActionGrant.role_id == role_id)
        )
        # Normalize to str to be safe if the DB column is int
        return {str(row[0]) for row in res.all()}

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.username == username, UserModel.is_deleted.is_(False)).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email, UserModel.is_deleted.is_(False)).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> Sequence[UserModel]:
        stmt = (
            select(UserModel)
            .where(UserModel.is_deleted.is_(False))
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    # -----------------------
    # Writes (no commit here)
    # -----------------------
    async def create(self, user: UserModel) -> UserModel:
        """
        Adds
        the
        user
        to
        session and flushes
        so
        PK is available.
        Caller
        must
        commit.
        """
        self.session.add(user)
        try:
            await self.session.flush()  # ensures PKs are populated
        except IntegrityError:
            # Let caller decide how to handle conflicts; typically they will rollback in their layer.
            raise
        # Optionally refresh if your ORM defaults compute fields on insert
        await self.session.refresh(user)
        return user

    async def update_fields(self, id_: int, fields: dict) -> Optional[UserModel]:
        """
        Partial
        update;
        returns
        the
        updated
        entity or None if not found.
        Caller
        must
        commit.
        """
        if not fields:
            return await self.get_by_id(id_)

        # Quick existence + not-deleted check
        exists_stmt = select(UserModel.id).where(
            UserModel.id == id_,
            UserModel.is_deleted.is_(False)
        ).limit(1)
        exists_res = await self.session.execute(exists_stmt)
        if not exists_res.scalar_one_or_none():
            return None

        stmt = (
            update(UserModel)
            .where(UserModel.id == id_)
            .values(**fields, updated_at=func.now())
            .returning(UserModel.id)
        )
        result = await self.session.execute(stmt)
        updated_id = result.scalar_one_or_none()
        if not updated_id:
            return None

        # Reload latest state
        return await self.get_by_id(updated_id)

    async def delete_user_and_return(self, id: int) -> Optional[UserModel]:
        """
        Soft - delete
        user and tombstone
        username / email
        to
        keep
        unique
        constraints
        free.
        Returns
        the
        updated
        row as ORM
        entity(
        from RETURNING).
        Caller
        must
        commit.
        """
        # 1) Read current values to compute new unique/tombstoned ones
        res = await self.session.execute(
            select(UserModel.email, UserModel.username)
            .where(UserModel.id == id, UserModel.is_deleted.is_(False))
            .limit(1)
        )
        curr = res.first()
        if not curr:
            return None

        new_email = make_deleted_email(curr.email, max_len=100)
        new_username = make_deleted_username(curr.username, max_len=50)

        # 2) UPDATE with guard + RETURNING full model
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
            return None

        # 3) Return updated entity; caller will commit
        return row

    async def bump_token_version(self, user_id: int) -> None:
        """
        Atomically
        bump
        token_version(used
        to
        invalidate
        all
        access
        tokens).
        Caller
        must
        commit.
        """
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                token_version=UserModel.token_version + 1,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.execute(stmt)
