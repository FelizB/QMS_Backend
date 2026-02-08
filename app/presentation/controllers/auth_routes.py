from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED

from app.application.use_cases.create_user_usecase import CreateUserUseCase
from app.core.db import get_session
from app.core.security import verify_password, create_access_token, create_refresh_token, \
    decode_refresh_token
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository as UserRepository
from app.presentation.dependencies.auth import get_current_user
from app.presentation.schemas.auth_schema import TokenOut, RefreshIn, UserOut
from app.presentation.schemas.user_schema import UserCreate

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/register", response_model=UserOut, status_code=HTTP_201_CREATED)
async def register(
        payload: UserCreate,
        session: AsyncSession = Depends(get_session),
        current_user=Depends(get_current_user),
):
    repo = UserRepository(session)
    # Disable public self register:
    uc = CreateUserUseCase(repo, allow_public_self_register=False)

    is_authenticated = current_user is not None
    current_is_admin = bool(getattr(current_user, "admin", False)) if current_user else False
    current_is_superuser = bool(getattr(current_user, "superuser", False)) if current_user else False

    user = await uc.execute(
        payload=payload,
        current_is_admin=current_is_admin,
        current_is_superuser=current_is_superuser,
        is_authenticated=is_authenticated,
    )
    return UserOut.model_validate(user, from_attributes=True)

    # OAuth2PasswordRequestForm expects application/x-www-form-urlencoded {username, password}


@auth_router.post("/token", response_model=TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    repo = UserRepository(session)
    # Decide if form.username carries email or username. Here we accept email first, else username.
    user = await repo.get_by_email(form.username) or await repo.get_by_username(form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token(user.id, {"username": user.username, "is_superuser": user.superuser})
    refresh = create_refresh_token(user.id)
    return TokenOut(access_token=access, refresh_token=refresh)


@auth_router.post("/refresh", response_model=TokenOut)
async def refresh_token(payload: RefreshIn = Body(...), session: AsyncSession = Depends(get_session)):
    try:
        data = decode_refresh_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    repo = UserRepository(session)
    user = await repo.get_by_id(int(user_id))
    if not user or not user.active:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    access = create_access_token(user.id, {"username": user.username, "is_superuser": user.superuser})
    # Optional: rotate refresh token (recommended). For now, reissue for convenience:
    refresh = create_refresh_token(user.id)
    return TokenOut(access_token=access, refresh_token=refresh)


@auth_router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    if current_user is None:  # happens if ENFORCE_AUTH=False or for docs paths
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.active,
        is_superuser=current_user.superuser,
    )


@auth_router.get("/me", response_model=UserOut)
async def me2(current_user=Depends(
    __import__("app.presentation.dependencies.auth", fromlist=["get_current_user"]).get_current_user)):
    u = current_user
    return UserOut(id=u.id, email=u.email, username=u.username, is_active=u.is_active, is_superuser=u.superuser)
