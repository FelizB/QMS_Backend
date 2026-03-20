from fastapi import Depends, HTTPException, status
from app.core.db import get_session
from app.presentation.dependencies.auth import get_current_user  # must provide user.id and is_superuser
from app.domain.security.role_policy import is_role_action_allowed


def require_role_action(action_name: str, entity_type: str | None = None):
    async def _inner(session=Depends(get_session), user=Depends(get_current_user)):
        superuser = bool(getattr(user, "is_superuser", False) or getattr(user, "superuser", False))
        ok = await is_role_action_allowed(
            session, user_id=user.id, action_name=action_name, entity_type=entity_type, superuser=superuser
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return {"user": user}

    return _inner
