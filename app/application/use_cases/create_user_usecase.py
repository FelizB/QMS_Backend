from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from starlette.status import HTTP_403_FORBIDDEN, HTTP_409_CONFLICT

from app.application.services.audit import audit
from app.core.security import get_password_hash  # ✅ adjust if your project uses a different module
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
from app.domain.utils.initials import generate_initials_and_colors
from app.infrastructure.models.role_matrix import Role, UserRole
from app.infrastructure.models.user_model import User as UserModel
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository


# ----------------- Helpers -----------------

def _norm(s: Optional[str]) -> Optional[str]:
    if isinstance(s, str):
        s2 = s.strip()
        return s2 if s2 else None
    return s


def _dict_obj(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


# ----------------- Role DB Helpers -----------------

async def get_role_by_id(session, role_id: int) -> Optional[Role]:
    return await session.get(Role, role_id)


async def get_default_role(session) -> Role:
    stmt = select(Role).where(Role.is_default.is_(True)).limit(1)
    role = (await session.execute(stmt)).scalars().first()
    if not role:
        raise HTTPException(400, "No default role configured (roles.is_default=true)")
    return role


async def get_user_primary_role_name(session, user_id: int) -> Optional[str]:
    """
    Uses UserRole mapping if present; falls back to users.role_id if needed.
    Minimal ranking for the policy: SUPERADMIN > ADMIN > other.
    """
    stmt = (
        select(func.upper(Role.name))
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    names = (await session.execute(stmt)).scalars().all()
    names = [n for n in names if n]

    if names:
        if "SUPERADMIN" in names:
            return "SUPERADMIN"
        if "ADMIN" in names:
            return "ADMIN"
        return names[0]

    # fallback: single role on user
    user = await session.get(UserModel, user_id)
    if user and getattr(user, "role_id", None):
        role = await session.get(Role, user.role_id)
        return role.name.upper() if role else None

    return None


def can_assign_role(creator_role_name: str, target_role_name: str) -> bool:
    """
    Strict policy (matches your statement):
    - SUPERADMIN can assign anything
    - ADMIN can assign USER only
    """
    creator = (creator_role_name or "").upper()
    target = (target_role_name or "").upper()

    if creator == "SUPERADMIN":
        return True

    if creator == "ADMIN":
        return target == "USER"  # ✅ strict rule

    return False


# ----------------- Use Case -----------------

class CreateUserUseCase:
    def __init__(self, repo: SQLAlchemyUserRepository, allow_public_self_register: bool = True):
        self.repo = repo
        self.allow_public_self_register = allow_public_self_register

    async def execute(
            self,
            *,
            payload,
            is_authenticated: bool,
            current_user_id: int | None = None,
            request: Request | None = None,
    ) -> UserModel:

        session = self.repo.session

        # -------- Decide selected role --------
        if not is_authenticated:
            if not self.allow_public_self_register:
                raise HTTPException(HTTP_403_FORBIDDEN, "Self registration is disabled")

            default_role = await get_default_role(session)
            selected_role_id = default_role.id
            selected_role_name = default_role.name.upper()

        else:
            if not current_user_id:
                raise HTTPException(HTTP_403_FORBIDDEN, "Missing current_user_id")

            creator_role_name = await get_user_primary_role_name(session, current_user_id)
            if not creator_role_name:
                raise HTTPException(HTTP_403_FORBIDDEN, "Creator has no role assigned")

            if not getattr(payload, "role_id", None):
                raise HTTPException(400, "A role must be selected")

            target_role = await get_role_by_id(session, int(payload.role_id))
            if not target_role:
                raise HTTPException(400, f"Invalid role_id: {payload.role_id}")

            selected_role_id = target_role.id
            selected_role_name = target_role.name.upper()

            if not can_assign_role(creator_role_name, selected_role_name):
                raise HTTPException(
                    HTTP_403_FORBIDDEN,
                    f"{creator_role_name} cannot assign role {selected_role_name}"
                )

        # -------- Normalize input --------
        email = (_norm(payload.email) or "").lower()
        username = _norm(payload.username)

        first_name = _norm(payload.first_name)
        last_name = _norm(payload.last_name)
        middle_name = _norm(payload.middle_name)
        gender = _norm(payload.gender)
        birthday = _norm(payload.birthday)

        department = _norm(payload.department)
        unit = _norm(payload.unit)

        phone = _norm(getattr(payload, "phone", None))
        site = _norm(getattr(payload, "site", None))
        address = _norm(getattr(payload, "address", None))
        country = _norm(getattr(payload, "country", None))

        primary_ws = _dict_obj(getattr(payload, "primary_worksite_info", None))
        secondary_ws = _dict_obj(getattr(payload, "secondary_worksite_info", None))

        # -------- Flags --------
        approved = True if is_authenticated else False
        active = True
        locked = False

        hashed_pw = get_password_hash(payload.password)
        init, init_colors = generate_initials_and_colors(first_name, last_name)

        # -------- Create ORM user --------
        user_model = UserModel(
            email=email,
            username=username,
            hashed_password=hashed_pw,
            initials=init,
            initials_colors=init_colors,
            active=active,
            approved=approved,
            locked=locked,
            department=department,
            unit=unit,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            gender=gender,
            birthday=birthday,
            phone=phone,
            site=site,
            address=address,
            country=country,
            primary_worksite_info=primary_ws,
            secondary_worksite_info=secondary_ws,
            role_id=selected_role_id,
        )

        try:
            user = await self.repo.create(user_model)
            if user is None:
                raise HTTPException(500, "Repository returned None during user creation")
            return user

        except IntegrityError as e:
            await session.rollback()
            orig = str(e.orig)

            if "uq_users_email" in orig or "users_email_key" in orig:
                msg = f"Email already exists: {email}"
            elif "uq_users_username" in orig or "users_username_key" in orig:
                msg = f"Username already exists: {username}"
            elif "uq_users_phone" in orig or "users_phone_key" in orig:
                msg = f"Phone already exists: {phone}"
            else:
                msg = f"Duplicate record :{orig}"

            await audit(
                session,
                request,
                title="Creation of user failed",
                entity_type=EntityType.USER,
                entity_id=0,
                action=ActivityAction.CREATE,
                outcome=ActivityOutcome.FAILED,
                error_message=msg,
                meta={"username": payload.username},
            )
            await session.commit()
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=msg)
