# app/presentation/controllers/approvals_route.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from app.domain.enum import ApprovalStatus, Action, EntityType
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.role_permissions import require_role_action as require_permission
from app.infrastructure.models.approval import ApprovalRequest
from app.infrastructure.models.project_model import Project
from app.core.db import get_session

approval_router = APIRouter(prefix="/approvals", tags=["Approvals"])


@approval_router.get("", summary="List pending approvals")
async def list_approvals(
        status_: ApprovalStatus | None = Query(None),
        entity_type: EntityType | None = Query(None),
        session=Depends(get_session),
        current_user=Depends(get_current_user),
):
    conds = []
    if status_:
        conds.append(ApprovalRequest.status == status_)
    if entity_type:
        conds.append(ApprovalRequest.entity_type == entity_type)
    q = select(ApprovalRequest).where(and_(*conds)) if conds else select(ApprovalRequest)
    q = q.order_by(ApprovalRequest.created_at.desc())
    rows = (await session.execute(q)).scalars().all()
    # map to DTO as needed
    return {"items": [serialize_approval(r) for r in rows]}


def serialize_approval(r: ApprovalRequest) -> dict:
    return {
        "id": r.id,
        "entityType": r.entity_type,
        "entityId": r.entity_id,
        "action": r.action,
        "status": r.status,
        "makerId": r.maker_id,
        "checkerId": r.checker_id,
        "createdAt": r.created_at,
        "payloadBefore": r.payload_before,
        "payloadAfter": r.payload_after,
    }


def forbid_self_approval(current_user_id: int, maker_id: int):
    if current_user_id == maker_id:
        raise HTTPException(status_code=403, detail="Self-approval is not allowed")


@approval_router.post("/{approval_id}/approve", status_code=200)
async def approve(
        approval_id: int,
        session=Depends(get_session),
        current_user=Depends(get_current_user),
        # Checker must have permission for the entity/action they approve:
        # You can also add a separate CHECK permission if you want
):
    ar = await session.get(ApprovalRequest, approval_id)
    if not ar or ar.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=404, detail="Approval not found or not pending")

    forbid_self_approval(current_user.id, ar.maker_id)

    # Apply change inside the route (commit at end)
    if ar.entity_type == EntityType.PROJECT:
        if ar.action == Action.CREATE:
            p = Project(**(ar.payload_after or {}))
            session.add(p)
            await session.flush()
            ar.entity_id = p.id

        elif ar.action == Action.UPDATE:
            p = await session.get(Project, ar.entity_id)
            if not p:
                raise HTTPException(status_code=404, detail="Entity missing")
            for k, v in (ar.payload_after or {}).items():
                setattr(p, k, v)
            await session.flush()

        elif ar.action == Action.DELETE:
            p = await session.get(Project, ar.entity_id)
            if p:
                await session.delete(p)

    # Extend for other EntityType as needed...

    ar.status = ApprovalStatus.APPROVED
    ar.checker_id = current_user.id
    await session.commit()
    return {"message": "approved", "id": approval_id, "entityId": ar.entity_id}


@approval_router.post("/{approval_id}/reject", status_code=200)
async def reject(
        approval_id: int,
        body: dict,
        session=Depends(get_session),
        current_user=Depends(get_current_user),
):
    ar = await session.get(ApprovalRequest, approval_id)
    if not ar or ar.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=404, detail="Approval not found or not pending")
    forbid_self_approval(current_user.id, ar.maker_id)
    ar.status = ApprovalStatus.REJECTED
    ar.checker_id = current_user.id
    ar.reason = (body or {}).get("reason")
    await session.commit()
    return {"message": "rejected"}
