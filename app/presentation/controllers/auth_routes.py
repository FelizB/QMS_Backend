from datetime import datetime, timezone
from typing import Optional
from jose import jwt
from fastapi import APIRouter, Depends, HTTPException, Body, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import Request
from sqlalchemy.sql.functions import user

from app.application.services.audit import audit
from app.application.services.audit_helper import AuditLogger, audit_span
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
from app.application.use_cases.create_user_usecase import CreateUserUseCase
from app.core.db import get_session
from app.core.deps import AuthzContext, get_auth_context
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token, decode_access_token,
)
from app.infrastructure.models.user_model import User
from app.infrastructure.repositories.TokenBlacklistRepository import TokenBlacklistRepository
from app.infrastructure.repositories.user_repository_sqlalchemy import (
    SQLAlchemyUserRepository as UserRepository,
    SQLAlchemyUserRepository,
)
from app.presentation.dependencies.auth import get_current_user
from app.presentation.dependencies.role_deriver import derive_role_flags
from app.presentation.schemas.auth_schema import TokenOut, RefreshIn, UserOut, LogoutOut, RoleOut, WorksiteInfo
from app.presentation.schemas.user_schema import UserCreate

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


# ----------------------------
# Helpers
# ----------------------------
async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate by username & password using your existing hash verifier."""
    stmt = select(User).where(User.username == username)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user or not getattr(user, "active", True) or getattr(user, "locked", False):
        return None
    if not verify_password(password, getattr(user, "hashed_password", "")):
        return None
    return user


def _build_role_out(role) -> RoleOut:
    """
    Construct RoleOut while respecting the existing schema.
    If RoleOut has 'code' in model_fields, include it; otherwise only (id, name).
    """
    payload = {"id": role.id}
    # Safely include fields that exist on the model/schema
    if hasattr(RoleOut, "model_fields"):
        fields = RoleOut.model_fields  # pydantic v2
        if "name" in fields:
            payload["name"] = getattr(role, "name", None)
        if "code" in fields:
            payload["code"] = getattr(role, "code", None)
    else:
        # fallback: assume at least name exists
        payload["name"] = getattr(role, "name", None)

    return RoleOut(**payload)


# ----------------------------
# Routes
# ----------------------------

@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
        payload: UserCreate,
        session: AsyncSession = Depends(get_session),
        current_user=Depends(get_current_user),
        request: Request = None,
):
    repo = UserRepository(session)
    uc = CreateUserUseCase(repo, allow_public_self_register=True)

    # Current user flags based on RBAC roles
    if current_user:
        flags = derive_role_flags(current_user)
        current_is_superuser = flags["is_superuser"]
        current_is_admin = flags["is_admin"]
        is_authenticated = True
    else:
        current_is_superuser = False
        current_is_admin = False
        is_authenticated = False

    user = await uc.execute(
        payload=payload,
        current_is_admin=current_is_admin,
        current_is_superuser=current_is_superuser,
        is_authenticated=is_authenticated,
    )
    await audit(
        session,
        request,
        title="registred new user",
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=ActivityAction.CREATE,
        outcome=ActivityOutcome.SUCCESS,
        actor_id=user.id,
        actor_first_name=user.first_name,
        meta={"username": user.username},
    )
    await session.commit()
    return UserOut.model_validate(user, from_attributes=True)


@auth_router.post("/refresh", response_model=TokenOut)
async def refresh_token(
        payload: RefreshIn = Body(...),
        session: AsyncSession = Depends(get_session),
        request: Request = None,
):
    # --- Defensive init to avoid UnboundLocalError ---
    data: dict | None = None
    user_id_raw: str | None = None
    token_typ: str | None = None
    jti: str | None = None
    sid_value: str | None = None

    # 1) Decode & validate refresh token
    try:
        data = decode_refresh_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Accept current 'typ' or legacy 'type'
    token_typ = (data.get("typ") or data.get("type") or "").lower()
    if token_typ != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    # 2) Load user & basic checks
    user_id_raw = data.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload (missing sub)")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload (bad sub)")

    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user or not getattr(user, "active", True) or getattr(user, "locked", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive/locked or not found")

    # If you later include versioning for refresh: compare here (optional, currently absent in your token)
    # jwt_ver = int(data.get("ver", getattr(user, "token_version", 1)))
    # if jwt_ver < int(getattr(user, "token_version", 1)):
    #     raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token invalidated, please log in again")

    # 3) Rotation: deny reuse by blacklisting this refresh token's JTI
    jti = data.get("jti")
    if not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token (missing jti)")

    exp_val = data.get("exp")
    if isinstance(exp_val, (int, float)):
        expires_at = datetime.fromtimestamp(int(exp_val), tz=timezone.utc)
    elif isinstance(exp_val, datetime):
        expires_at = exp_val
    else:
        expires_at = datetime.now(timezone.utc)

    bl_repo = TokenBlacklistRepository(session)
    if await bl_repo.is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    await bl_repo.add(user_id=user.id, jti=jti, token_type="refresh", expires_at=expires_at)

    # 4) Resolve role (supports direct FK or mapping), compute rv
    # If you added get_effective_role as per earlier patch, use it; otherwise use direct FK.
    try:
        get_effective_role = getattr(repo, "get_effective_role")
    except Exception:
        get_effective_role = None

    if callable(get_effective_role):
        role = await get_effective_role(user)
    else:
        role = await repo.get_role_by_id(user.role_id)

    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")

    rv = int(getattr(role, "rv", 1))

    # Keep same session id from the old refresh
    sid_value = data.get("sid")

    # 5) Re-issue tokens — your create_* functions are keyword-only
    new_access = create_access_token(
        version=getattr(user, "token_version", 1),
        subject=str(user.id),
        role_id=role.id,
        rv=rv,
        sid=sid_value,  # reuse same session id
        extra={
            "username": user.username,
            "is_superuser": getattr(user, "superuser", False),
            "ver": int(getattr(user, "token_version", 1)),

        },
    )
    new_refresh = create_refresh_token(
        subject=str(user.id),
        sid=sid_value,
    )

    await audit(
        session,
        request,
        title="loged in successfully",
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=ActivityAction.REFRESH,
        outcome=ActivityOutcome.SUCCESS,
        actor_id=user.id,
        actor_first_name=user.first_name,
        meta={"username": user.username},
    )

    await session.commit()
    return TokenOut(access_token=new_access, refresh_token=new_refresh)


@auth_router.post(
    "/logout",
    response_model=LogoutOut,
    status_code=status.HTTP_200_OK,
    response_description="Logged out",
)
async def logout(
        payload: RefreshIn | None = Body(None),
        request: Request = None,
        current_user=Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
):
    if current_user is None:
        await audit(
            session,
            request,
            title="Logout failed",
            entity_type=EntityType.USER,
            entity_id=0,
            action=ActivityAction.LOGIN,
            outcome=ActivityOutcome.FAILED,
            error_message="Not authenticated",
            meta={"username": payload.username},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    bl_repo = TokenBlacklistRepository(session)
    blacklisted_refresh = False
    blacklisted_access = False

    # 1) Best-effort: blacklist provided refresh token's JTI
    if payload and payload.refresh_token:
        try:
            data = decode_refresh_token(payload.refresh_token)
            token_typ = (data.get("typ") or data.get("type") or "").lower()
            if token_typ == "refresh" and str(data.get("sub")) == str(current_user.id):
                jti = data.get("jti")
                exp_val = data.get("exp")
                if isinstance(exp_val, (int, float)):
                    expires_at = datetime.fromtimestamp(int(exp_val), tz=timezone.utc)
                elif isinstance(exp_val, datetime):
                    expires_at = exp_val
                else:
                    expires_at = datetime.now(timezone.utc)
                if jti:
                    await bl_repo.add(user_id=current_user.id, jti=jti, token_type="refresh", expires_at=expires_at)
                    blacklisted_refresh = True
        except Exception:
            pass  # ignore malformed/foreign refresh tokens

    # 2) Also blacklist the CURRENT ACCESS token (from Authorization header)
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        access_token = auth_header.split(" ", 1)[1].strip()
        try:
            a_data = decode_access_token(access_token)
            if (a_data.get("typ") or a_data.get("type")) == "access" and str(a_data.get("sub")) == str(current_user.id):
                a_jti = a_data.get("jti")
                a_exp = a_data.get("exp")
                if a_jti and a_exp:
                    if isinstance(a_exp, (int, float)):
                        a_expires_at = datetime.fromtimestamp(int(a_exp), tz=timezone.utc)
                    elif isinstance(a_exp, datetime):
                        a_expires_at = a_exp
                    else:
                        a_expires_at = datetime.now(timezone.utc)
                    await bl_repo.add(user_id=current_user.id, jti=a_jti, token_type="access", expires_at=a_expires_at)
                    blacklisted_access = True
        except Exception:
            pass  # ignore malformed/foreign access tokens

    # 3) Global invalidation: bump token_version to nuke all outstanding access tokens
    await UserRepository(session).bump_token_version(current_user.id)
    await session.commit()

    msg = "Logged out successfully. All access tokens invalidated."
    if blacklisted_refresh:
        msg += " Current refresh token revoked."
    if blacklisted_access:
        msg += " Current access token revoked."
    if not (blacklisted_refresh or blacklisted_access):
        msg += " No token(s) provided to revoke."

    await audit(
        session,
        request,
        title="loged out successfully",
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=ActivityAction.LOGOUT,
        outcome=ActivityOutcome.SUCCESS,
        actor_id=user.id,
        actor_first_name=user.first_name,
        meta={"username": user.username},
    )

    return LogoutOut(code="LOGOUT_SUCCESS", message=msg, details=None)


@auth_router.get("/me", response_model=UserOut)
async def me(
        ctx: AuthzContext = Depends(get_auth_context),
        session: AsyncSession = Depends(get_session),
):
    if isinstance(ctx, tuple):
        ctx = ctx[0]

    repo = SQLAlchemyUserRepository(session)
    user = await repo.get_by_id(ctx.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    role = await repo.get_role_by_id(ctx.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Role not found")

    # ---- Helpers for defaults (only used if your model lacks values) ----
    def _compute_initials(first: str | None, last: str | None, username: str) -> str:
        f = (first or "").strip()
        l = (last or "").strip()
        if f or l:
            return f[:1].upper() + l[:1].upper()
        # fallback: take first 2 letters of username
        u = (username or "").strip()
        return (u[:2] or "U").upper()

    def _default_initials_color(username: str) -> str:
        # stable pseudo-color based on username; replace with your palette function if you have one
        palette = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22",
                   "#17BECF"]
        idx = (sum(ord(c) for c in username) or 0) % len(palette)
        return palette[idx]

    # ---- Build RoleOut according to your schema ----
    role_kwargs = {"id": int(role.id)}
    if "name" in getattr(RoleOut, "model_fields", {}):
        role_kwargs["name"] = getattr(role, "name", None)
    if "code" in getattr(RoleOut, "model_fields", {}):
        role_kwargs["code"] = getattr(role, "code", None)
    role_out = RoleOut(**role_kwargs)

    # ---- Gather user fields with safe defaults for required ones ----
    first_name = getattr(user, "first_name", None)
    last_name = getattr(user, "last_name", None)
    username = getattr(user, "username", "") or ""

    initials_val = getattr(user, "initials", None) or _compute_initials(first_name, last_name, username)
    initials_colors_val = getattr(user, "initials_colors", None) or _default_initials_color(username)
    gender_val = getattr(user, "gender", None) or "Unspecified"

    # NOTE: Your schema requires id:int; ensure we pass int (not str)
    return UserOut(
        id=int(getattr(user, "id")),
        email=getattr(user, "email"),
        username=username,
        active=bool(getattr(user, "active", True)),
        approved=bool(getattr(user, "approved", False)),
        locked=bool(getattr(user, "locked", False)),
        department=getattr(user, "department", None),
        unit=getattr(user, "unit", None),
        first_name=first_name,
        middle_name=getattr(user, "middle_name", None),
        last_name=last_name,
        initials=initials_val,
        initials_colors=initials_colors_val,
        gender=gender_val,
        birthday=getattr(user, "birthday", None),
        phone=getattr(user, "phone", None),
        site=getattr(user, "site", None),
        address=getattr(user, "address", None),
        country=getattr(user, "country", None),
        primary_worksite_info=getattr(user, "primary_worksite_info", None) or WorksiteInfo(),  # default_factory
        secondary_worksite_info=getattr(user, "secondary_worksite_info", None) or WorksiteInfo(),  # default_factory
        role=role_out,
        permissions=sorted(list(getattr(ctx, "permissions", []))),
        flags={
            "is_active": bool(getattr(user, "is_active", getattr(user, "active", True))),
            "mfa_enabled": bool(getattr(user, "mfa_enabled", False)),
            "password_reset_required": bool(getattr(user, "password_reset_required", False)),
        },
        session={"sid": getattr(ctx, "sid", None), "rv": getattr(ctx, "rv", None)},
    )


@auth_router.post("/token", response_model=TokenOut)
async def login(
        form: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_session),
        request: Request = None,
):
    # Early audit on bad creds
    user = await authenticate_user(session, form.username, form.password)
    if not user:
        await audit(
            session,
            request,
            title="Login failed",
            entity_type=EntityType.USER,
            entity_id=0,
            action=ActivityAction.LOGIN,
            outcome=ActivityOutcome.FAILED,
            error_message="Invalid credentials",
            meta={"username": form.username},
        )
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    repo = SQLAlchemyUserRepository(session)
    role = await repo.get_role_by_id(user.role_id)
    if not role:
        await audit(
            session,
            request,
            title="Login failed",
            entity_type=EntityType.USER,
            entity_id=0,
            action=ActivityAction.LOGIN,
            outcome=ActivityOutcome.FAILED,
            error_message="Invalid Role ID",
            meta={"username": form.username},
        )
        await session.commit()
        raise HTTPException(status_code=400, detail="A role must be assigned")

    rv = int(getattr(role, "rv", 1))

    # Issue tokens
    access = create_access_token(
        subject=str(user.id),
        role_id=role.id,
        rv=rv,
        sid=None,
        extra={
            "username": user.username,
            "is_superuser": getattr(user, "superuser", False),
            "amr": ["pwd"],
            "ver": int(getattr(user, "token_version", 1)),
        },
    )
    from jose import jwt as jose_jwt
    sid_value = jose_jwt.get_unverified_claims(access).get("sid")
    refresh = create_refresh_token(subject=str(user.id), sid=sid_value)

    # Success audit
    await audit(
        session,
        request,
        title="login Successful",
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=ActivityAction.LOGIN,
        outcome=ActivityOutcome.SUCCESS,
        actor_id=user.id,
        actor_first_name=user.first_name,
        meta={"username": user.username},
    )

    await session.commit()

    return TokenOut(access_token=access, refresh_token=refresh)
