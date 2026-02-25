# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

RESERVED = {"sub", "type", "exp", "iat", "jti", "ver"}  # <-- NEW


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _exp(minutes: int) -> datetime:
    return _now() + timedelta(minutes=minutes)


def _exp_days(days: int) -> datetime:
    return _now() + timedelta(days=days)


def _merge_extra(base: Dict[str, Any], extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not extra:
        return base
    # Do NOT allow overwriting reserved JWT claims
    safe_extra = {k: v for k, v in extra.items() if k not in RESERVED}
    base.update(safe_extra)
    return base


def create_access_token(subject: str | int, *, token_version: int, extra: Optional[Dict[str, Any]] = None) -> str:
    iat = _now()
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "ver": int(token_version),  # <-- NEW
        "jti": uuid4().hex,  # <-- NEW
        "iat": int(iat.timestamp()),  # <-- NEW
        "exp": _exp(settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    payload = _merge_extra(payload, extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | int, *, token_version: int, extra: Optional[Dict[str, Any]] = None) -> str:
    iat = _now()
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "ver": int(token_version),  # <-- NEW
        "jti": uuid4().hex,  # <-- NEW
        "iat": int(iat.timestamp()),  # <-- NEW
        "exp": _exp_days(settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    payload = _merge_extra(payload, extra)
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_compat(token: str, key: str) -> Dict[str, Any]:
    """
    Works with both PyJWT and python-jose:
      - PyJWT: supports top-level `leeway=...`
      - python-jose: expects `options={'leeway': ...}`
    """
    verify_opts = {"verify_aud": False}
    leeway = settings.JWT_LEEWAY_SECONDS
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[settings.JWT_ALGORITHM],
            options=verify_opts,
            leeway=leeway,
        )
    except TypeError:
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
