from typing import Optional
from fastapi import Depends, HTTPException
from starlette.status import HTTP_403_FORBIDDEN
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.presentation.dependencies.auth import get_current_user  # adjust
from app.infrastructure.models.role_matrix import Role, UserRole, RoleAction, RoleActionGrant


async def _get_user_role_ids(session: AsyncSession, user_id: int) -> list[int]:
    stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
    return list((await session.execute(stmt)).scalars().all())


async def _get_action_id(session: AsyncSession, action_name: str) -> Optional[int]:
    stmt = select(RoleAction.id).where(func.upper(RoleAction.name) == action_name.upper())
    return (await session.execute(stmt)).scalar_one_or_none()


async def _has_grant(
        session: AsyncSession,
        role_ids: list[int],
        action_id: int,
        entity_type: Optional[str],
) -> bool:
    """
    Checks if any of the user's roles has an allow grant for:
      - exact entity_type, OR
      - global grant (entity_type is NULL)
    """
    stmt = select(RoleActionGrant.allow).where(
        and_(
            RoleActionGrant.role_id.in_(role_ids),
            RoleActionGrant.action_id == action_id,
            or_(
                RoleActionGrant.entity_type == entity_type,
                RoleActionGrant.entity_type.is_(None),
            ),
        )
    )

    rows = (await session.execute(stmt)).scalars().all()
    # allow if any True exists; if you support explicit deny rows later, handle precedence.
    return any(bool(x) for x in rows)


def require_permission(action: str, entity_type: Optional[str] = None):
    """
    FastAPI dependency factory.
    Usage: Depends(require_permission("VIEW", "ROLE"))
    """

    async def _guard(
            session: AsyncSession = Depends(get_session),
            current_user=Depends(get_current_user),
    ):
        if not current_user:
            raise HTTPException(HTTP_403_FORBIDDEN, "Not authenticated")

        role_ids = await _get_user_role_ids(session, current_user.id)
        if not role_ids:
            raise HTTPException(HTTP_403_FORBIDDEN, "No roles assigned")

        action_id = await _get_action_id(session, action)
        if not action_id:
            raise HTTPException(HTTP_403_FORBIDDEN, f"Unknown action: {action}")

        ok = await _has_grant(session, role_ids, action_id, entity_type)
        if not ok:
            raise HTTPException(HTTP_403_FORBIDDEN, "Insufficient permissions")

        return True

    return _guard
