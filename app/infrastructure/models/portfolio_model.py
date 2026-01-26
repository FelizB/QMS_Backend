from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, String, Text, Index, event
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    workspace_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    artifact_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    concurrency_guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.text("true"))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.text("false"))
    # Soft delete fields
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.false())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    custom_properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True,
                                                                        server_default=sa.text("'{}'::jsonb"))

    last_updated_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    programs: Mapped[list["Program"]] = relationship(
        "Program",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # If you do NOT want a single global default portfolio, delete this index.
        Index(
            "uq_portfolio_default_singleton",
            "is_default",
            unique=True,
            postgresql_where=sa.text("is_default IS TRUE"),
            info={"alembic_autogenerate": False},
        ),
    )


# Auto-refresh last_updated_date at Python layer too (safety net)
@event.listens_for(Portfolio, "before_update")
def portfolio_touch(mapper, connection, target):
    target.last_updated_date = func.now()
