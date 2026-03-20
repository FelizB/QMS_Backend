# app/infrastructure/models/activity_log.py# datetime import datetime
import enum
from datetime import datetime

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Integer, Index, text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enum import EntityType, ActivityAction, ActivityOutcome
from app.infrastructure.models.base import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Make non-null if you enforce strict tenancy
    org_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type_enum"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)

    action: Mapped[ActivityAction] = mapped_column(
        SAEnum(
            ActivityAction,
            name="activity_action_enum",
            native_enum=False,
            values_callable=lambda obj: [member.value for member in obj],  # USE VALUES!
            create_constraint=False
        ),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)

    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # 'metadata' is the DB column; Python attribute is 'meta'
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # Outcome + error context (to log both success and failures)
    outcome: Mapped[ActivityOutcome] = mapped_column(
        SAEnum(
            ActivityOutcome,
            name="activity_outcome_enum",
            native_enum=False,
            values_callable=lambda obj: [member.value for member in obj],
            create_constraint=False,
        ),
        nullable=False,
        server_default="success",
        # keep as literal to match migration
    )
    error_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(800), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_activity_log_org_created", "org_id", "created_at"),
        Index("ix_activity_log_created_desc", "created_at"),
        Index("ix_activity_log_entity", "entity_type", "entity_id"),
        # You can add outcome index later if you query by failures frequently:
        # Index("ix_activity_log_outcome_created", "outcome", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ActivityLog id={self.id} type={self.entity_type} action={self.action} "
            f"outcome={self.outcome} at={self.created_at}>"
        )
