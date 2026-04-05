from fastapi import Request

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import user

from app.application.services.audit import audit
from app.application.use_cases.delete_user_usecase import DeleteUserUseCase
from app.core.db import get_session
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome, RoleAction
from app.domain.security.rbac import require_permission
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository
from app.presentation.dependencies.auth import get_current_user
from app.presentation.schemas.auth_schema import UserOut
from app.presentation.schemas.user_schema import UserSummary, UserUpdate, UserDeleteResponse

user_router = APIRouter(prefix="/users", tags=["users"],
                        dependencies=[Depends(require_permission("VIEW", EntityType.USER.value))])


def get_user_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyUserRepository(session)


@user_router.get("/", dependencies=[Depends(require_permission("INITIATE", EntityType.USER.value))],
                 response_model=list[UserSummary])
async def list_users(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        repo=Depends(get_user_repo)
):
    rows = await repo.list(limit=limit, offset=offset)
    if not rows:
        raise HTTPException(status_code=404, detail="No User not found")
    return [UserSummary.model_validate(r) for r in rows]


@user_router.get("/by-username/{username}", response_model=UserSummary)
async def get_user_by_username(username: str, repo=Depends(get_user_repo)):
    row = await repo.get_by_username(username)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)


@user_router.get("/by-id/{id:int}", response_model=UserSummary)
async def get_user_by_id(id: int, repo=Depends(get_user_repo)):
    row = await repo.get_by_id(id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)


@user_router.get("/by-id-detailed/{id:int}", response_model=UserOut)
async def get_user_by_id_detailed(id: int, repo=Depends(get_user_repo)):
    row = await repo.get_by_id(id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(row)


@user_router.get("/by-email/{email}", response_model=UserSummary)
async def get_user_by_email(email: str, repo=Depends(get_user_repo)):
    row = await repo.get_by_email(email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)


@user_router.patch("/{id}", response_model=UserSummary,
                   dependencies=[Depends(require_permission("INITIATE", EntityType.USER.value))])
async def update_user(id: int, payload: UserUpdate, repo=Depends(get_user_repo), request: Request = None,
                      session: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    fields = payload.model_dump(exclude_unset=True)
    # Normalize optional fields if present
    if "Email" in fields and fields["Email"]:
        fields["Email"] = fields["Email"].strip().lower()

    try:
        row = await repo.update_fields(id, fields)
        await audit(
            session,
            request,
            title="updated Successful",
            entity_type=EntityType.USER,
            entity_id=id,
            action=ActivityAction.UPDATE,
            outcome=ActivityOutcome.SUCCESS,
            actor_id=current_user.id,
            actor_first_name=current_user.first_name,
            meta={"username": current_user.username},
        )
        await session.commit()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Username or Email already exists")

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserSummary.model_validate(row)


@user_router.delete("/{id}", dependencies=[Depends(require_permission("INITIATE", EntityType.USER.value))],
                    response_model=UserDeleteResponse, status_code=200)
async def delete_user(id: int, repo=Depends(get_user_repo), session: AsyncSession = Depends(get_session),
                      request: Request = None, current_user=Depends(get_current_user), ):
    du = DeleteUserUseCase(repo)
    try:
        resp = await du.soft_delete(id)
        await audit(
            session,
            request,
            title="login Successful",
            entity_type=EntityType.USER,
            entity_id=id,
            action=ActivityAction.DELETE,
            outcome=ActivityOutcome.SUCCESS,
            actor_id=current_user.id,
            actor_first_name=current_user.first_name,
            meta={"username": current_user.username},
        )
        await session.commit()
        return resp
    except ValueError as ex:
        await audit(
            session,
            request,
            title="Login failed",
            entity_type=EntityType.USER,
            entity_id=0,
            action=ActivityAction.LOGIN,
            outcome=ActivityOutcome.FAILED,
            error_message="Invalid credentials",
            meta={"id": id},
        )
        await session.commit()
        raise HTTPException(status_code=409, detail=str(ex))
