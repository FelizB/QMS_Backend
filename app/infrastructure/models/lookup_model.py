from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TestCaseStatusLkp(Base):
    __tablename__ = "test_case_statuses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # e.g., "draft"
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g., "Draft"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    color_hex: Mapped[str] = mapped_column(String(7), nullable=True)  # "#RRGGBB"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    external_key: Mapped[str | None] = mapped_column(String(100), nullable=True)


class PriorityLkp(Base):
    __tablename__ = "priorities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # "critical"
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)  # "Critical"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    color_hex: Mapped[str | None] = mapped_column(String(7))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(100))


class TestCaseTypeLkp(Base):
    __tablename__ = "test_case_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # "functional"
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)  # "Functional"
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    color_hex: Mapped[str | None] = mapped_column(String(7))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(100))
