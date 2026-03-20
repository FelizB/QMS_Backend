from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Dict

import sqlalchemy as sa
from sqlalchemy import String, Integer, Boolean, DateTime, text, Date
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import UniqueConstraint

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    initials: Mapped[str] = mapped_column(String(2), nullable=False)
    initials_colors = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.true())
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.false())
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.false())
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    department: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)

    gender: Mapped[Optional[str]] = mapped_column(String(16))
    birthday: Mapped[Optional[date]] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(),
                                                 onupdate=sa.func.now())

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.false())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    phone: Mapped[Optional[str]] = mapped_column(String(32), unique=True)
    site: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[Optional[str]] = mapped_column(String(255))

    primary_worksite_info: Mapped[Dict[str, object]] = mapped_column(JSONB, nullable=False,
                                                                     server_default=text("'{}'::jsonb"))
    secondary_worksite_info: Mapped[Dict[str, object]] = mapped_column(JSONB, nullable=False,
                                                                       server_default=text("'{}'::jsonb"))

    # ❗ NEW: SINGLE ROLE
    role_id: Mapped[int] = mapped_column(sa.ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )
