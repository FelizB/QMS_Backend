from typing import Optional, Any, Dict, List
from fastapi import Request

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from starlette.status import HTTP_403_FORBIDDEN, HTTP_409_CONFLICT

from app.application.services.audit import audit
from app.core.security import get_password_hash
from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
from app.domain.utils.initials import generate_initials_and_colors

from app.infrastructure.models.user_model import User as UserModel
from app.infrastructure.repositories.user_repository_sqlalchemy import SQLAlchemyUserRepository

# Role Matrix Models
from app.infrastructure.models.role_matrix import Role, UserRole


# ----------------- Helpers -----------------

def _norm(s: Optional[str]) -> Optional[str]:
    if isinstance(s, str):
        s2 = s.strip()
        return s2 if s2 else None
    return s


def _dict_obj(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_roles_list(payload) -> List[str]:
    """
    Accepts payload.roles: list[str]
    Defaults to USER if missing.
    """
    if hasattr(payload, "roles") and isinstance(payload.roles, list):
        roles = [str(r).strip().upper() for r in payload.roles if str(r).strip()]
        if roles:
            return roles
    return ["USER"]


# ----------------- Role Assignment -----------------

SUPERADMIN = "SUPERADMIN"
ADMIN = "ADMIN"
USER = "USER"


async def _resolve_role_ids(session, role_names: List[str]) -> Dict[str, int]:
    if not role_names:
        return {}
    stmt = select(Role.name, Role.id).where(Role.name.in_(role_names))
    rows = (await session.execute(stmt)).all()
    return {name.upper(): rid for (name, rid) in rows}


async def _existing_user_role_ids(session, user_id: int) -> set[int]:
    stmt = select(UserRole.role_id).where(UserRole.user_id == user_id)
    return set((await session.execute(stmt)).scalars().all())


def _filter_roles_by_creator(
        requested: List[str],
        *,
        current_is_superuser: bool,
        current_is_admin: bool,
) -> List[str]:
    if current_is_superuser:
        return requested

    if current_is_admin:
        return [r for r in requested if r != SUPERADMIN]

    return [USER]


async def _assign_roles_to_user(
        session,
        user_id: int,
        requested_roles: List[str],
        *,
        current_is_superuser: bool,
        current_is_admin: bool,
) -> List[str]:
    requested = [r.upper().strip() for r in requested_roles if r]
    requested = _filter_roles_by_creator(
        requested,
        current_is_superuser=current_is_superuser,
        current_is_admin=current_is_admin,
    )

    # Resolve to IDs
    map_name_to_id = await _resolve_role_ids(session, requested)

    # Check for unknown roles
    unknown = [r for r in requested if r not in map_name_to_id]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown roles: {', '.join(unknown)}")

    existing = await _existing_user_role_ids(session, user_id)
    to_insert = []

    for r in requested:
        rid = map_name_to_id[r]
        if rid not in existing:
            to_insert.append(UserRole(user_id=user_id, role_id=rid))

    if to_insert:
        session.add_all(to_insert)
        await session.flush()

    return requested


# ----------------- CreateUserUseCase -----------------
class CreateUserUseCase:
    """
    FINAL SINGLE-ROLE VERSION
    """

    def __init__(self, repo: SQLAlchemyUserRepository, allow_public_self_register=True, request=Request):
        self.repo = repo
        self.allow_public_self_register = allow_public_self_register

    async def execute(
            self,
            *,
            payload,
            current_is_admin: bool,
            current_is_superuser: bool,
            is_authenticated: bool,
            USER_ROLE_ID=5,
            request: Request = None,
    ) -> UserModel:

        session = self.repo.session

        # -------- ACCESS RULES --------
        if not is_authenticated:
            # Self-register → force USER role
            selected_role_id = USER_ROLE_ID

        else:
            if not current_is_admin and not current_is_superuser:
                raise HTTPException(403, "Only ADMIN or SUPERADMIN can create users")

            # Validate they sent a role
            if not hasattr(payload, "role_id") or payload.role_id is None:
                raise HTTPException(400, "A role must be selected")

            selected_role_id = payload.role_id

        # -------- RESOLVE ROLE --------
        role = await session.get(Role, selected_role_id)
        if not role:
            raise HTTPException(400, f"Invalid role_id: {selected_role_id}")

        role_name = role.name.upper()

        # -------- PERMISSION LOGIC --------
        if current_is_admin and role_name == "SUPERADMIN":
            raise HTTPException(403, "Admin cannot assign SUPERADMIN")

        # -------- NORMALIZE INPUT --------
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

        # -------- FLAGS --------
        approved = True if (current_is_superuser or current_is_admin) else False
        active = True
        locked = False

        hashed_pw = get_password_hash(payload.password)
        init, init_colors = generate_initials_and_colors(first_name, last_name)

        # -------- CREATE ORM USER --------
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
            return user


        except IntegrityError as e:
            await session.rollback()

            # Extract readable message from Postgres
            orig = str(e.orig)

            # Common Postgres patterns
            if "uq_users_email" in orig or "users_email_key" in orig:
                msg = f"Email already exists: {email}"

            elif "uq_users_username" in orig or "users_username_key" in orig:
                msg = f"Username already exists: {username}"

            elif "uq_users_phone" in orig or "users_phone_key" in orig:
                msg = f"Phone already exists: {phone}"

            else:
                # fallback generic
                msg = f"Duplicate record :{orig}"

            # Audit AFTER rollback
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

            raise HTTPException(status_code=409, detail=msg)
