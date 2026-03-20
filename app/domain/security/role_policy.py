from sqlalchemy import select, or_
from app.infrastructure.models.role_matrix import UserRole, Role, RoleAction, RoleActionGrant


async def user_role_names(session, user_id: int) -> list[str]:
    q = (
        select(Role.name)
        .select_from(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    return (await session.execute(q)).scalars().all()


async def is_role_action_allowed(
        session,
        *,
        user_id: int,
        action_name: str,
        entity_type: str | None = None,
        superuser: bool = False
) -> bool:
    if superuser:
        return True

    roles = await user_role_names(session, user_id)
    if not roles:
        return False

    # Resolve action id
    act_id = (await session.execute(
        select(RoleAction.id).where(RoleAction.name == action_name)
    )).scalar_one_or_none()
    if act_id is None:
        return False

    # Any role with allow=True and (entity_type match OR global None)
    q = (
        select(RoleActionGrant.allow)
        .select_from(RoleActionGrant)
        .join(Role, Role.id == RoleActionGrant.role_id)
        .where(
            Role.name.in_(roles),
            RoleActionGrant.action_id == act_id,
            RoleActionGrant.allow.is_(True),
            or_(RoleActionGrant.entity_type == entity_type, RoleActionGrant.entity_type.is_(None)),
        )
        .limit(1)
    )
    return bool((await session.execute(q)).scalar_one_or_none() is True)
