# app/presentation/dependencies/actor_ctx.py
from typing import TypedDict, Optional
from fastapi import Depends
from sqlalchemy import inspect as sa_inspect

from app.presentation.dependencies.auth import get_current_user  # your existing auth dependency


class ActorCtx(TypedDict, total=False):
    actor_id: Optional[int]
    actor_first_name: Optional[str]
    org_id: Optional[int]


async def get_actor_ctx(user=Depends(get_current_user)) -> ActorCtx:
    """
    Return a plain dict with actor context, avoiding ORM lazy-loads outside a safe context.
    """
    ctx: ActorCtx = {}

    # Try to read the primary key via identity (does not lazy-load)
    try:
        insp = sa_inspect(user)
        if insp is not None and insp.identity:
            ctx["actor_id"] = insp.identity[0]
    except Exception:
        pass

    # Best-effort read of simple attributes (preferably eager-loaded by get_current_user)
    for attr, key in (("first_name", "actor_first_name"), ("org_id", "org_id")):
        try:
            val = getattr(user, attr, None)
            if val is not None:
                ctx[key] = val
        except Exception:
            # If attribute is expired/lazy, skip to prevent async IO at wrong time
            pass

    return ctx
