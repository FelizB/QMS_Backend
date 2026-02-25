# app/presentation/dependencies/auth.py
from fastapi import Security, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token
from app.core.settings import settings
from app.infrastructure.repositories.TokenBlacklistRepository import TokenBlacklistRepository
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository as UserRepository

bearer_scheme = HTTPBearer(auto_error=False)
DOCS_PATHS = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}


def http_401(code: str, message: str, detail: str):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message, "detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
        session: AsyncSession = Security(get_session),
):
    if request.url.path in DOCS_PATHS:
        return None
    if not settings.ENFORCE_AUTH:
        return None
    if not credentials:
        http_401("NO_AUTH", "Not authenticated", "Missing Authorization: Bearer token")
    if credentials.scheme != "Bearer" or not credentials.credentials:
        http_401("INVALID_AUTH_SCHEME", "Invalid Authorization scheme", "Bearer required")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        http_401("TOKEN_EXPIRED", "Token expired", "Access token expired")
    except JWTError as e:
        http_401("INVALID_TOKEN", "Invalid token", str(e))

    if payload.get("type") != "access":
        http_401("WRONG_TOKEN_TYPE", "Wrong token type", "Access token required")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        http_401("INVALID_SUB", "Invalid token subject", "Missing/invalid sub")

    user = await UserRepository(session).get_by_id(user_id)
    if not user or not user.active or user.locked:
        http_401("USER_INVALID", "User not allowed", "User not found, inactive or locked")

    jwt_ver = int(payload.get("ver", 0))
    if jwt_ver < user.token_version:
        http_401("TOKEN_INVALIDATED", "Token invalidated", "Please log in again")

    # Usually don't blacklist access JTIs if access TTL is short.
    return user
