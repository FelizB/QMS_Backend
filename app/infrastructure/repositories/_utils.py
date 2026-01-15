
from __future__ import annotations
from uuid import uuid4

def _token(n: int = 8) -> str:
    return str(uuid4()).replace("-", "")[:n]

def make_deleted_username(original: str, max_len: int) -> str:
    # Minimal, unique suffix
    suffix = f"__del__{_token()}"          # e.g., __del__a1b2c3d4 (15 chars)
    keep = max_len - len(suffix)
    if keep < 1:
        return suffix[:max_len]
    return original[:keep] + suffix

def make_deleted_email(original: str, max_len: int) -> str:
    """
    Convert "name@domain" -> "name+deleted.<token>@domain"
    Truncate the local-part if needed so the whole address fits in max_len.
    """
    if "@" not in original:
        # fallback: treat as username if it's not an email
        return make_deleted_username(original, max_len)

    local, domain = original.split("@", 1)
    suffix = f"+deleted.{_token()}"        # e.g., +deleted.a1b2c3d4
    # Reserve 1 for '@'
    base_len = len(suffix) + 1 + len(domain)
    keep = max_len - base_len
    if keep < 1:
        # worst case: trim domain if absolutely necessary, but try to keep '@'
        new_local = ""
    else:
        new_local = local[:keep]
    return f"{new_local}{suffix}@{domain}"
