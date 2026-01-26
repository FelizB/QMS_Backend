from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import UniqueConstraint

from .base import Base  # your declarative Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    test_case_status_id: Mapped[int] = mapped_column(Integer,
                                                     nullable=False)  # FK to status lookup table if you have one
    test_case_type_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to type lookup table if you have one
    priority_id: Mapped[Optional[int]] = mapped_column(Integer)
    release_id: Mapped[Optional[int]] = mapped_column(Integer)  # FK to releases if modeled

    folder_id: Mapped[Optional[int]] = mapped_column(Integer)  # FK to folders if modeled

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    steps: Mapped[List["TestStep"]] = relationship(
        "TestStep",
        back_populates="test_case",
        cascade="all, delete-orphan",
        order_by="TestStep.sequence",
        lazy="selectin",  # avoids MissingGreenlet
    )

    __table_args__ = (
        # Partial unique index for active rows only (Postgres)
        Index(
            "uq_test_case_name_per_project_active",
            "project_id",
            "name",
            unique=True,
            postgresql_where=(~(is_deleted))  # is_deleted = false
        ),
    )


class TestStep(Base):
    __tablename__ = "test_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("test_case_id", "sequence", name="uq_test_step_sequence_per_case"),
    )
