from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Enum, ForeignKey, Integer, JSON, Index, text
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import (
    String, Enum as SAEnum, ForeignKey, Integer, Index, text, DateTime
)

from app.domain.enum import EntityType, ActivityAction
from app.infrastructure.models.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Make this NOT NULL if you enforce tenancy
    org_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type_enum"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)

    action: Mapped[ActivityAction] = mapped_column(
        SAEnum(ActivityAction, name="activity_action_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_activity_log_org_created", "org_id", "created_at"),
        Index("ix_activity_log_created_desc", "created_at"),
        Index("ix_activity_log_entity", "entity_type", "entity_id"),
    )
