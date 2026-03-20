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


def _base_claims(version: int, subject: str | int, role_id: int, rv: int, sid: Optional[str] = None) -> Dict[
    str, Any]:
    return {
        "type": "access",
        "iss": settings.JWT_ISS,
        "aud": settings.JWT_AUD,
        "sub": subject,  # user id
        "jti": uuid4().hex,
        "ver": version,
        "sid": sid or str(uuid4()),
        "iat": int(_now().timestamp()),
        "role_id": role_id,
        "exp": _exp(settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "rv": rv,  # role version
    }


def create_access_token(*, version: int, subject: str, role_id: int, rv: int, sid: Optional[str] = None,

                        extra: Optional[Dict[str, Any]] = None,
                        minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    payload = _base_claims(version=version, subject=subject, role_id=role_id, rv=rv, sid=sid)
    exp = _now() + timedelta(minutes=minutes)
    payload["exp"] = int(exp.timestamp())
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, subject: str, sid: str) -> str:
    payload = {
        "iss": settings.JWT_ISS,
        "aud": settings.JWT_AUD,
        "sub": subject,
        "jti": uuid4().hex,
        "sid": sid,
        "iat": int(_now().timestamp()),
        "typ": "refresh",
        "exp": int((_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
    }

    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_compat(token: str, key: str) -> Dict[str, Any]:
    """
    Works with both PyJWT and python-jose:
      - PyJWT: supports top-level `leeway=...`
      - python-jose: expects `options={'leeway': ...}`
    """
    verify_opts = {"verify_aud": True, "verify_iss": True}
    leeway = settings.JWT_LEEWAY_SECONDS
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUD,
            issuer=settings.JWT_ISS,
            options=verify_opts,
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
