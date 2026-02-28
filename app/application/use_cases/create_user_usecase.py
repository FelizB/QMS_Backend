from typing import Optional, Any, Dict, List

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.status import HTTP_403_FORBIDDEN, HTTP_409_CONFLICT

from app.core.security import get_password_hash
from app.domain.utils.initials import generate_initials_and_colors
from app.infrastructure.models.user_model import User as UserModel  # adjust import path if needed
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository  # or your concrete repo


def _norm(s: Optional[str]) -> Optional[str]:
    """Trim string; keep None for non-strings or empty after trim."""
    if isinstance(s, str):
        s2 = s.strip()
        return s2 if s2 != "" else None
    return s


def _list_str(v: Any) -> List[str]:
    """Ensure a list[str] with trimmed, non-empty strings."""
    if isinstance(v, list):
        out: List[str] = []
        for x in v:
            sx = str(x).strip()
            if sx:
                out.append(sx)
        return out
    return []


def _dict_obj(v: Any) -> Dict[str, Any]:
    """Ensure a plain dict; otherwise {}."""
    return v if isinstance(v, dict) else {}


class CreateUserUseCase:
    """
    Policy:
      - superuser: may create admin/superuser/normal (payload flags honored)
      - admin (not superuser): may create only normal (flags forced False)
      - authenticated normal: forbidden (403)
      - unauthenticated: self-register as normal (if allowed)
    """

    def __init__(self, repo: SQLAlchemyUserRepository, allow_public_self_register: bool = True):
        self.repo = repo
        self.allow_public_self_register = allow_public_self_register

    async def execute(
            self,
            *,
            payload,  # Pydantic UserCreate
            current_is_admin: bool,
            current_is_superuser: bool,
            is_authenticated: bool,
    ) -> UserModel:

        email = (_norm(payload.email) or "").lower()
        username = _norm(payload.username)
        department = _norm(payload.department)
        role = _norm(payload.role)
        unit = _norm(payload.unit)
        first_name = _norm(payload.first_name)
        middle_name = _norm(payload.middle_name)
        last_name = _norm(payload.last_name)
        rss_token = _norm(payload.rss_token)
        gender = _norm(payload.gender)
        birthday = _norm(payload.birthday)

        phone = _norm(getattr(payload, "phone", None))
        site = _norm(getattr(payload, "site", None))
        address = _norm(getattr(payload, "address", None))
        country = _norm(getattr(payload, "country", None))
        primary_worksite = _norm(getattr(payload, "primary_worksite", None))
        secondary_worksite = _norm(getattr(payload, "secondary_worksite", None))
        primary_worksite_info = _dict_obj(getattr(payload, "primary_worksite_info", None))  # dict
        secondary_worksite_info = _dict_obj(getattr(payload, "secondary_worksite_info", None))  # dict

        # Decide flags
        if current_is_superuser:
            admin_flag = bool(getattr(payload, "admin", False))
            superuser_flag = bool(getattr(payload, "superuser", False))
            approved = True
            active = True
        elif current_is_admin:
            # Admin can only create normal users
            admin_flag = False
            superuser_flag = False
            approved = True
            active = True
        else:
            # Normal users cannot create; unauthenticated may self-register if enabled
            if is_authenticated:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Only superuser/admin can create users")
            if not self.allow_public_self_register:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Self registration is disabled")
            admin_flag = False
            superuser_flag = False
            approved = False  # you can require manual approval
            active = True

        locked = False
        hashed = get_password_hash(payload.password)

        # Initials & colors
        init, init_colors = generate_initials_and_colors(
            payload.first_name,
            payload.last_name,
        )

        # Build ORM model instance
        # NOTE: JSONB columns are NOT NULL with server defaults—passing [] / {} is safe too.
        user_model = UserModel(
            email=email,
            username=username,
            initials=init,
            initials_colors=init_colors,
            hashed_password=hashed,
            admin=admin_flag,
            superuser=superuser_flag,
            active=active,
            approved=approved,
            locked=locked,
            department=department,
            role=role,
            unit=unit,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            rss_token=rss_token,
            gender=gender,
            birthday=birthday,
            phone=phone,
            site=site,
            address=address,
            country=country,
            primary_worksite=primary_worksite,
            secondary_worksite=secondary_worksite,
            primary_worksite_info=primary_worksite_info,  # JSONB {}
            secondary_worksite_info=secondary_worksite_info,  # JSONB {}
        )

        # Create via repository (commits inside)
        try:
            return await self.repo.create(user_model)

        except IntegrityError as e:
            # SQLAlchemy context
            stmt = getattr(e, 'statement', None)
            params = getattr(e, 'params', None)

            # DBAPI (psycopg/asyncpg) exception
            orig = getattr(e, 'orig', None)
            pgcode = getattr(orig, 'pgcode', None)  # e.g., '23505' for unique_violation
            diag = getattr(orig, 'diag', None)  # Diagnostic object (may be None)

            constraint = getattr(diag, 'constraint_name', None)
            schema = getattr(diag, 'schema_name', None)
            table = getattr(diag, 'table_name', None)
            column = getattr(diag, 'column_name', None)
            detail = getattr(diag, 'detail', None)
            message_primary = getattr(diag, 'message_primary', None)

            # Log (replace prints with your logger)
            print("SQLALCHEMY STMT:", stmt)
            print("PARAMS:", params)
            print("PGCODE:", pgcode)
            print("DIAG:", {
                "message_primary": message_primary,
                "detail": detail,
                "schema": schema,
                "table": table,
                "column": column,
                "constraint": constraint,
            })

            # Friendly messages
            if pgcode == '23505':  # unique_violation (e.g., email or phone unique)
                # You can branch by constraint to be more specific:
                # if constraint == 'ix_users_phone_unique': ...
                raise HTTPException(status_code=409, detail=f"Unique violation on {constraint or table}")
            elif pgcode == '23502':  # not_null_violation
                raise HTTPException(status_code=400, detail=f"NULL in NOT NULL column: {column}")
            elif pgcode == '23503':  # foreign_key_violation
                raise HTTPException(status_code=400, detail=f"Foreign key violation on {constraint}")
            else:
                raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Username or email already registered")
