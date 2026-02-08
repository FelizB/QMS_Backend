# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict

from jose import jwt
from passlib.context import CryptContext

from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _exp(minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _exp_days(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def create_access_token(subject: str | int, extra: Optional[Dict[str, Any]] = None) -> str:
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "exp": _exp(settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | int, extra: Optional[Dict[str, Any]] = None) -> str:
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "exp": _exp_days(
            settings.JWT_REFRESH_SECRET_KEY and settings.REFRESH_TOKEN_EXPIRE_DAYS or settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_compat(token: str, key: str) -> Dict[str, Any]:
    """
    Works with both PyJWT and python-jose:
      - PyJWT: supports top-level `leeway=...`
      - python-jose: expects `options={'leeway': ...}`
    """
    # Common options
    verify_opts = {"verify_aud": False}
    leeway = settings.JWT_LEEWAY_SECONDS

    # Try PyJWT-style first
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[settings.JWT_ALGORITHM],
            options=verify_opts,
            leeway=leeway,  # PyJWT supports this kwarg
        )
    except TypeError:
        # Fallback for python-jose: pass leeway via options
        jose_opts = dict(verify_opts)
        jose_opts["leeway"] = leeway
        return jwt.decode(
            token,
            key,
            algorithms=[settings.JWT_ALGORITHM],
            options=jose_opts,
        )


def decode_access_token(token: str) -> Dict[str, Any]:
    return _decode_compat(token, settings.JWT_SECRET_KEY)


def decode_refresh_token(token: str) -> Dict[str, Any]:
    return _decode_compat(token, settings.JWT_REFRESH_SECRET_KEY)
