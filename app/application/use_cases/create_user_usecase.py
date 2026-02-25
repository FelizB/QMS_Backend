from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.status import HTTP_403_FORBIDDEN, HTTP_409_CONFLICT

from app.core.security import get_password_hash
from app.infrastructure.models.user_model import User as UserModel  # adjust import path if needed
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository  # or your concrete repo


def _norm(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s


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
        # Normalize
        email = _norm(payload.email).lower()
        username = _norm(payload.username)
        department = _norm(payload.department)
        role = _norm(payload.role)
        unit = _norm(payload.unit)
        first_name = _norm(payload.first_name)
        middle_name = _norm(payload.middle_name)
        last_name = _norm(payload.last_name)
        rss_token = _norm(payload.rss_token)

        # Decide flags
        if current_is_superuser:
            admin_flag = bool(payload.admin)
            superuser_flag = bool(payload.superuser)
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

        # Build full ORM model instance
        user_model = UserModel(
            email=email,
            username=username,
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
        )

        # Create via repository (commits inside)
        try:
            return await self.repo.create(user_model)

        except IntegrityError as e:
            # SQLAlchemy context
            stmt = getattr(e, 'statement', None)
            params = getattr(e, 'params', None)

            # DBAPI (psycopg2) exception
            orig = getattr(e, 'orig', None)
            pgcode = getattr(orig, 'pgcode', None)  # e.g., '23505' for unique_violation
            diag = getattr(orig, 'diag', None)  # Diagnostic object (may be None)

            constraint = getattr(diag, 'constraint_name', None)
            schema = getattr(diag, 'schema_name', None)
            table = getattr(diag, 'table_name', None)
            column = getattr(diag, 'column_name', None)
            detail = getattr(diag, 'detail', None)  # often very helpful
            message_primary = getattr(diag, 'message_primary', None)  # main message

            # Log everything for debugging
            # (Use your logger, avoid printing in prod)
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

            # Optionally, map specific codes to friendly messages
            if pgcode == '23505':  # unique_violation
                raise HTTPException(status_code=409, detail=f"Unique violation on {constraint or table}")
            elif pgcode == '23502':  # not_null_violation
                raise HTTPException(status_code=400, detail=f"NULL in NOT NULL column: {column}")
            elif pgcode == '23503':  # foreign_key_violation
                raise HTTPException(status_code=400, detail=f"Foreign key violation on {constraint}")
            else:
                # Re-raise or wrap with raw message for dev
                # Unique (email/username) conflicts or races → return consistent 409
                raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Username or email already registered")
