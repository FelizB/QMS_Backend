from __future__ import annotations

from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # credentials / identity
    username: Mapped[str] = mapped_column(String(128), name="Username", unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), name="Email", unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # flags
    admin: Mapped[bool] = mapped_column(Boolean, name="Admin", nullable=False, server_default=sa.sql.false())
    active: Mapped[bool] = mapped_column(Boolean, name="Active", nullable=False, server_default=sa.sql.true())
    approved: Mapped[bool] = mapped_column(Boolean, name="Approved", nullable=False, server_default=sa.sql.false())
    locked: Mapped[bool] = mapped_column(Boolean, name="Locked", nullable=False, server_default=sa.sql.false())

    # org info
    department: Mapped[str] = mapped_column(String(255), name="Department", nullable=False)
    unit: Mapped[str] = mapped_column(
        String(255), name="Unit", nullable=False
    )

    # names
    first_name: Mapped[str] = mapped_column(
        String(255), name="FirstName", nullable=False
    )
    middle_name: Mapped[Optional[str]] = mapped_column(
        String(255), name="MiddleName", nullable=True
    )
    last_name: Mapped[str] = mapped_column(
        String(255), name="LastName", nullable=False
    )

    # tokens
    rss_token: Mapped[Optional[str]] = mapped_column(
        String(255), name="RssToken", nullable=True
    )

    # audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="created_at",
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        name="updated_at",
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    # soft delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        name="is_deleted",
        nullable=False,
        server_default=sa.sql.false(),
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        name="deleted_at",
        nullable=True,
    )
