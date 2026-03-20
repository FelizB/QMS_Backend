# app/security/deps.py
from typing import Any, Dict, Iterable, List, Optional, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import RolePermsCache as role_perms_cache
from app.core.db import get_session as get_db  # your existing session dep
from app.core.security import decode_access_token as decode_and_validate, decode_access_token
from app.infrastructure.repositories.TokenBlacklistRepository import TokenBlacklistRepository
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer(auto_error=False)


class AuthzContext:
    __slots__ = ("user_id", "role_id", "rv", "sid", "jti", "permissions")

    def __init__(self, user_id: int, role_id: int, rv: int, sid: str, jti: str, permissions: Set[str]):
        self.user_id = user_id
        self.role_id = role_id
        self.rv = rv
        self.sid = sid
        self.jti = jti
        self.permissions = frozenset(permissions)


async def _load_permissions(db: AsyncSession, role_id: int, rv: int) -> Set[str]:
    repo = SQLAlchemyUserRepository(db)
    perms = await role_perms_cache.get(role_id, rv)
    if perms is not None:
        return perms
    perms = await repo.get_role_permissions(db, role_id)
    await role_perms_cache.set(role_id, rv, perms)
    return perms


def _as_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token", "detail": f"{name} must be an integer"},
        )


async def get_auth_context(
        creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
) -> AuthzContext:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Decode and validate standard claims (iss, aud, exp)
    try:
        claims: Dict[str, Any] = decode_access_token(creds.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token", "detail": str(e)},
        )

    # Enforce access token type
    token_typ = (claims.get("typ") or claims.get("type") or "").lower()
    if token_typ != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    # Required claims
    sid = claims.get("sid")
    jti = claims.get("jti")
    if not sid or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    # 🔒 Denylist check for ACCESS tokens (logout/force-logout should add this jti)
    bl_repo = TokenBlacklistRepository(db)
    if await bl_repo.is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # Normalize IDs for DB queries
    user_id = _as_int(claims.get("sub"), "sub")
    role_id = _as_int(claims.get("role_id"), "role_id")
    rv = _as_int(claims.get("rv"), "rv")

    # 🔒 Version must be present in access token and match DB
    ver_claim = claims.get("ver", None)
    if ver_claim is None:
        # If you absolutely must allow old tokens, you could warn/allow; safer is to fail closed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token (missing version)")

    try:
        ver = int(ver_claim)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token (bad version)")

    repo = SQLAlchemyUserRepository(db)

    # User checks
    user = await repo.get_by_id(user_id)
    if not user or not getattr(user, "active", True) or getattr(user, "locked", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    # Version check vs DB
    if ver < int(getattr(user, "token_version", 1)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalidated — please log in")

    # Role & role-version (rv) checks
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Role not found")
    role_rv = int(getattr(role, "rv", 1))
    if role_rv != rv:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalid — role updated")

    # Effective permissions
    perms = await repo.get_role_permissions(role_id)

    return AuthzContext(
        user_id=user_id,
        role_id=role_id,
        rv=rv,
        sid=sid,
        jti=jti,
        permissions=set(perms),
    )


def authorize(required: Iterable[str]):
    """
    Use as:
      - per-route guard: dependencies=[Depends(authorize(['users:view']))]
      - or as a parameter: ctx: AuthzContext = Depends(authorize(['users:view']))
    Returns ONLY AuthzContext (no tuples).
    """
    required_set = set(required)

    async def _dep(ctx: AuthzContext = Depends(get_auth_context)) -> AuthzContext:
        if not required_set.issubset(ctx.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden — missing required permissions",
            )
        # ✅ No trailing comma here!
        return ctx

    return _dep
