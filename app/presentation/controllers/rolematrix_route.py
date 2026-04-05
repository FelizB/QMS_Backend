from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.presentation.schemas.role_matrix_schema import RoleOut, ActionOut, ActionIn, GrantOut, GrantIn, RoleIn
from app.core.db import get_session
from app.infrastructure.models.role_matrix import Role, RoleAction, RoleActionGrant

role_router = APIRouter(prefix="/roles", tags=["role_matrix"])


# ---------- Roles ----------
@role_router.get("/roles", response_model=list[RoleOut])
async def list_roles(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Role))).scalars().all()
    return [RoleOut(id=r.id, name=r.name, is_default=r.is_default) for r in rows]


@role_router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(body: RoleIn, session: AsyncSession = Depends(get_session)):
    existing = (await session.execute(select(Role).where(Role.name == body.name))).scalar_one_or_none()
    if existing:
        return RoleOut(id=existing.id, name=existing.name, is_default=existing.is_default)
    r = Role(name=body.name, is_default=False)
    session.add(r);
    await session.flush();
    await session.commit()
    return RoleOut(id=r.id, name=r.name, is_default=r.is_default)


@role_router.delete("/roles/{role_id}", status_code=204)
async def delete_role(role_id: int, session: AsyncSession = Depends(get_session)):
    r = await session.get(Role, role_id)
    if not r:
        raise HTTPException(404, "Role not found")
    if r.is_default:
        raise HTTPException(400, "Default roles cannot be deleted")
    # Also removes grants via FK cascade
    await session.delete(r);
    await session.commit()
    return {}


# ---------- Actions ----------
@role_router.get("/actions", response_model=list[ActionOut])
async def list_actions(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(RoleAction))).scalars().all()
    return [ActionOut(id=a.id, name=a.name, is_default=a.is_default) for a in rows]


@role_router.post("/actions", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
async def create_action(body: ActionIn, session: AsyncSession = Depends(get_session)):
    existing = (await session.execute(select(RoleAction).where(RoleAction.name == body.name))).scalar_one_or_none()
    if existing:
        return ActionOut(id=existing.id, name=existing.name, is_default=existing.is_default)
    a = RoleAction(name=body.name, is_default=False)
    session.add(a);
    await session.flush();
    await session.commit()
    return ActionOut(id=a.id, name=a.name, is_default=a.is_default)


@role_router.delete("/actions/{action_id}", status_code=204)
async def delete_action(action_id: int, session: AsyncSession = Depends(get_session)):
    a = await session.get(RoleAction, action_id)
    if not a:
        raise HTTPException(404, "Action not found")
    if a.is_default:
        raise HTTPException(400, "Default actions cannot be deleted")
    await session.delete(a);
    await session.commit()
    return {}


# ---------- Grants ----------
@role_router.get("/grants", response_model=list[GrantOut])
async def list_grants(
        entity_type: Optional[str] = Query(None),
        session: AsyncSession = Depends(get_session),
):
    q = (
        select(Role.name, RoleAction.name, RoleActionGrant.entity_type, RoleActionGrant.allow)
        .select_from(RoleActionGrant)
        .join(Role, Role.id == RoleActionGrant.role_id)
        .join(RoleAction, RoleAction.id == RoleActionGrant.action_id)
    )
    if entity_type is None:
        q = q.where(RoleActionGrant.entity_type.is_(None))
    else:
        q = q.where(RoleActionGrant.entity_type == entity_type)
    rows = (await session.execute(q)).all()
    return [GrantOut(role=r[0], action=r[1], entity_type=r[2], allow=r[3]) for r in rows]


@role_router.put("/grants", response_model=GrantOut)
async def upsert_grant(body: GrantIn, session: AsyncSession = Depends(get_session)):
    role = (await session.execute(select(Role).where(Role.name == body.role))).scalar_one_or_none()
    if not role:
        raise HTTPException(404, f"Role {body.role} not found")
    action = (await session.execute(select(RoleAction).where(RoleAction.name == body.action))).scalar_one_or_none()
    if not action:
        raise HTTPException(404, f"Action {body.action} not found")

    # Find existing grant
    existing = (await session.execute(
        select(RoleActionGrant).where(
            RoleActionGrant.role_id == role.id,
            RoleActionGrant.action_id == action.id,
            RoleActionGrant.entity_type.is_(
                None) if body.entity_type is None else RoleActionGrant.entity_type == body.entity_type
        )
    )).scalar_one_or_none()

    if existing:
        existing.allow = body.allow
    else:
        session.add(RoleActionGrant(
            role_id=role.id,
            action_id=action.id,
            entity_type=body.entity_type,
            allow=body.allow
        ))
    await session.commit()

    return GrantOut(role=role.name, action=action.name, entity_type=body.entity_type, allow=body.allow)
