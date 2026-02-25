from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Body, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_204_NO_CONTENT

from app.application.use_cases.create_user_usecase import CreateUserUseCase
from app.core.db import get_session
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.infrastructure.repositories.TokenBlacklistRepository import TokenBlacklistRepository
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository as UserRepository
from app.presentation.dependencies.auth import get_current_user
from app.presentation.schemas.auth_schema import TokenOut, RefreshIn, UserOut, LogoutOut
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
    uc = CreateUserUseCase(repo, allow_public_self_register=True)

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
async def login(
        form: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_session),
):
    repo = UserRepository(session)
    # Accept email or username
    user = await repo.get_by_email(form.username) or await repo.get_by_username(form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # ✅ Include token_version in both tokens (ver + jti are set in token payload)
    access = create_access_token(
        user.id,
        token_version=user.token_version,
        extra={"username": user.username, "is_superuser": user.superuser},
    )
    refresh = create_refresh_token(
        user.id,
        token_version=user.token_version,
    )

    # If you log audits, commit here; otherwise harmless
    await session.commit()
    return TokenOut(access_token=access, refresh_token=refresh)


@auth_router.post("/refresh", response_model=TokenOut)
async def refresh_token(
        payload: RefreshIn = Body(...),
        session: AsyncSession = Depends(get_session),
):
    # 1) Validate refresh token
    try:
        data = decode_refresh_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    # 2) Load user & enforce token_version
    user_id_raw = data.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or not user.active or user.locked:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User inactive/locked or not found")

    jwt_ver = int(data.get("ver", 0))
    if jwt_ver < int(getattr(user, "token_version", 1)):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token invalidated, please log in again")

    # 3) Rotation: blacklist the current refresh JTI (prevents reuse)
    jti = data.get("jti")
    if not jti:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # exp can arrive as int or datetime depending on jose version
    exp_val = data.get("exp")
    if isinstance(exp_val, (int, float)):
        expires_at = datetime.fromtimestamp(int(exp_val), tz=timezone.utc)
    elif isinstance(exp_val, datetime):
        expires_at = exp_val
    else:
        # Fallback to 'now' if decoding gave unexpected type
        expires_at = datetime.now(timezone.utc)

    bl_repo = TokenBlacklistRepository(session)
    # If already blacklisted, reject (refresh token reuse)
    if await bl_repo.is_blacklisted(jti):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    await bl_repo.add(user_id=user.id, jti=jti, token_type="refresh", expires_at=expires_at)

    # 4) Issue new pair (same token_version)
    new_access = create_access_token(
        user.id,
        token_version=user.token_version,
        extra={"username": user.username, "is_superuser": user.superuser},
    )
    new_refresh = create_refresh_token(
        user.id,
        token_version=user.token_version,
    )

    await session.commit()
    return TokenOut(access_token=new_access, refresh_token=new_refresh)


@auth_router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return UserOut.model_validate(current_user, from_attributes=True)


@auth_router.post("/logout",
                  response_model=LogoutOut,
                  status_code=status.HTTP_200_OK,  # <-- custom status code here
                  response_description="Logged out",
                  )
async def logout(
        payload: RefreshIn | None = Body(None),
        current_user=Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    bl_repo = TokenBlacklistRepository(session)
    blacklisted = False

    # Best-effort: if the client sends the refresh token, blacklist its JTI
    if payload and payload.refresh_token:
        try:
            data = decode_refresh_token(payload.refresh_token)
            if data.get("type") == "refresh" and str(data.get("sub")) == str(current_user.id):
                jti = data.get("jti")
                exp_val = data.get("exp")
                if isinstance(exp_val, (int, float)):
                    expires_at = datetime.fromtimestamp(int(exp_val), tz=timezone.utc)
                elif isinstance(exp_val, datetime):
                    expires_at = exp_val
                else:
                    expires_at = datetime.now(timezone.utc)
                if jti:
                    await bl_repo.add(
                        user_id=current_user.id,
                        jti=jti,
                        token_type="refresh",
                        expires_at=expires_at,
                    )
                    blacklisted = True
        except Exception:
            # ignore malformed or foreign refresh tokens
            pass

    # Global invalidation: bump token_version to nuke all access tokens immediately
    await UserRepository(session).bump_token_version(current_user.id)
    await session.commit()

    msg = "Logged out successfully. All access tokens invalidated."
    if blacklisted:
        msg += " Current refresh token revoked."
    else:
        msg += " No refresh token provided."

    return LogoutOut(
        code="LOGOUT_SUCCESS",
        message=msg,
        details=None
    )
