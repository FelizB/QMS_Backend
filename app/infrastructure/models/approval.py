from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, JSON, DateTime, func, Boolean

from app.infrastructure.models.base import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)

    action: Mapped[str] = mapped_column(String(32), index=True)

    payload_before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_after: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    maker_id: Mapped[int] = mapped_column(Integer)
    checker_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    requires_maker_checker: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, onupdate=func.now())
