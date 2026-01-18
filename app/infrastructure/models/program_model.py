from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index, event
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # ProgramId

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="RESTRICT"), nullable=False)
    project_template_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    workspace_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    artifact_type_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    concurrency_guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.text("true"))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.text("false"))

    custom_properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True,
                                                                        server_default=sa.text("'{}'::jsonb"))

    last_updated_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="programs", lazy="joined")

    __table_args__ = (
        # Only one default Program per Portfolio
        Index(
            "uq_program_default_per_portfolio",
            "portfolio_id",
            unique=True,
            postgresql_where=sa.text("is_default IS TRUE"),
            info={"alembic_autogenerate": False}
        ),
        # Optional: name unique within portfolio
        Index("uq_program_name_per_portfolio",
              "portfolio_id", "name",
              unique=True,
              info={"alembic_autogenerate": False}),
    )


# Auto-refresh last_updated_date at Python layer too (safety net)
@event.listens_for(Program, "before_update")
def program_touch(mapper, connection, target):
    target.last_updated_date = func.now()
