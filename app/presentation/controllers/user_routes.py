from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.db import get_session
from app.presentation.schemas.user_schema import UserCreate, UserOut, UserSummary, UserUpdate, UserDeleteResponse
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository
from app.application.use_cases.create_user import CreateUserUseCase

router = APIRouter(prefix="/users", tags=["users"])

def get_user_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyUserRepository(session)

@router.post("/", response_model=UserSummary, status_code=201)
async def create_user(payload: UserCreate, repo = Depends(get_user_repo)):
    uc = CreateUserUseCase(repo)
    try:
        return await uc.execute(payload)
    except ValueError as ex:
        raise HTTPException(status_code=409, detail=str(ex))

@router.get("/", response_model=list[UserSummary])
async def list_users(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        repo = Depends(get_user_repo)
):
    rows = await repo.list(limit=limit, offset=offset)
    if not rows:
        raise HTTPException(status_code=404, detail="No User not found")
    return [UserSummary.model_validate(r) for r in rows]

@router.get("/by-username/{username}", response_model=UserSummary)
async def get_user_by_username(username: str, repo = Depends(get_user_repo)):
    row = await repo.get_by_username(username)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)

@router.get("/by-id/{id:int}", response_model=UserSummary)
async def get_user_by_id(id: int, repo = Depends(get_user_repo)):
    row = await repo.get_by_id(id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)

@router.get("/by-email/{email}", response_model=UserSummary)
async def get_user_by_email(email: str, repo = Depends(get_user_repo)):
    row = await repo.get_by_email(email)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)

@router.patch("/{id}", response_model=UserSummary)
async def update_user(id: int, payload: UserUpdate, repo = Depends(get_user_repo)):
    fields = payload.model_dump(exclude_unset=True)
    # Normalize optional fields if present
    if "Email" in fields and fields["Email"]:
        fields["Email"] = fields["Email"].strip().lower()

    try:
        row = await repo.update_fields(id, fields)
    except IntegrityError:
        # unique constraint conflict on Email/Username
        raise HTTPException(status_code=409, detail="Username or Email already exists")

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSummary.model_validate(row)


@router.delete("/{id}", response_model=UserDeleteResponse, status_code=200)
async def delete_user(id: int, repo = Depends(get_user_repo)):
    deleted_user = await repo.delete_user_and_return(id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User with ID provided not found")
    return {"message":"User deleted successfully",
            "data":UserOut.model_validate(deleted_user, from_attributes=True)
            }