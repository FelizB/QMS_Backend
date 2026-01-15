from __future__ import annotations
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import sqlalchemy as sa
from .base import Base

class Project(Base):
    __tablename__ = "projects"

    # Keys / Ids
    project_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_template_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    project_group_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # Dates / status
    creation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.true())
    status: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Planning fields
    working_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    working_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    non_working_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    percent_complete: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Soft delete fields
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.sql.false())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)