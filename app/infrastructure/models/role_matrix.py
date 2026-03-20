from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, ForeignKey, UniqueConstraint
from app.infrastructure.models.base import Base  # your Declarative Base


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SUPERADMIN, ADMIN, MANAGER, USER
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # protect from deletion


class RoleAction(Base):
    __tablename__ = "role_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # INITIATE/VIEW/REVIEW/APPROVE
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # protect from deletion


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        index=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )


class RoleActionGrant(Base):
    """
    Grants: a role can perform an action, optionally scoped to an entity type.
    entity_type NULL means global (applies everywhere).
    """
    __tablename__ = "role_action_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("role_actions.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    allow: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("role_id", "action_id", "entity_type", name="uq_role_action_scope"),)
