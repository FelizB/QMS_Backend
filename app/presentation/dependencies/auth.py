# app/presentation/dependencies/auth.py
from fastapi import Security, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from app.core.db import get_session
from app.core.security import decode_access_token
from app.core.settings import settings
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository as UserRepository

bearer_scheme = HTTPBearer(auto_error=False)  # keep auto_error=False so we can return clean 401s

DOCS_PATHS = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}


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
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    if credentials.scheme != "Bearer" or not credentials.credentials:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid Authorization scheme")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await UserRepository(session).get_by_id(int(user_id))
    if not user or not user.active or user.locked:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="User inactive or locked")

    return user
