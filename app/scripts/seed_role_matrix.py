from sqlalchemy import select
from app.infrastructure.models.role_matrix import Role, RoleAction, RoleActionGrant
from sqlalchemy.ext.asyncio import AsyncSession

# Defaults from your enums
DEFAULT_ROLES = ["SUPERADMIN", "ADMIN", "MANAGER", "USER"]
DEFAULT_ACTIONS = ["INITIATE", "VIEW", "REVIEW", "APPROVE"]

# Global (entity-agnostic) grants (adjust freely)
DEFAULT_GLOBAL_GRANTS: dict[str, list[str]] = {
    "SUPERADMIN": ["INITIATE", "VIEW", "REVIEW", "APPROVE"],
    "ADMIN": ["INITIATE", "VIEW", "REVIEW"],
    "MANAGER": ["INITIATE", "VIEW", "REVIEW", "APPROVE"],
    "USER": ["INITIATE"],  # all roles can INITIATE; VIEW intentionally not default for USER
}


async def seed_role_matrix(session: AsyncSession):
    # Insert roles if missing
    role_ids: dict[str, int] = {}
    for r in DEFAULT_ROLES:
        role = (await session.execute(select(Role).where(Role.name == r))).scalar_one_or_none()
        if not role:
            role = Role(name=r, is_default=True)
            session.add(role)
            await session.flush()
        role_ids[r] = role.id

    # Insert actions if missing
    action_ids: dict[str, int] = {}
    for a in DEFAULT_ACTIONS:
        act = (await session.execute(select(RoleAction).where(RoleAction.name == a))).scalar_one_or_none()
        if not act:
            act = RoleAction(name=a, is_default=True)
            session.add(act)
            await session.flush()
        action_ids[a] = act.id

    # Insert default grants if missing (global scope)
    for role_name, actions in DEFAULT_GLOBAL_GRANTS.items():
        rid = role_ids[role_name]
        for a in actions:
            aid = action_ids[a]
            exists = (await session.execute(
                select(RoleActionGrant.id).where(
                    RoleActionGrant.role_id == rid,
                    RoleActionGrant.action_id == aid,
                    RoleActionGrant.entity_type.is_(None)
                )
            )).scalar_one_or_none()
            if not exists:
                session.add(RoleActionGrant(role_id=rid, action_id=aid, entity_type=None, allow=True))

    await session.commit()
