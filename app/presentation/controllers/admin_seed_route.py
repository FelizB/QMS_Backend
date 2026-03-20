# app/presentation/controllers/admin_seed_route.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.presentation.dependencies.auth import get_current_user
from app.scripts.seed_role_matrix import seed_role_matrix

seed_router = APIRouter(prefix="/admin/seed", tags=["admin_seed"])


@seed_router.post("/role-matrix")
async def run_seed(
        session: AsyncSession = Depends(get_session),
        user=Depends(get_current_user),
):
    if not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    await seed_role_matrix(session)
    return {"message": "seeded"}
