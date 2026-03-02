from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Enum as SAEnum, Integer, DateTime, text
from app.domain.enum import TaskType, TaskPriority, TaskStatus
from app.infrastructure.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    type: Mapped[TaskType] = mapped_column(SAEnum(TaskType, name="task_type", native_enum=False))
    priority: Mapped[TaskPriority] = mapped_column(SAEnum(TaskPriority, name="task_priority", native_enum=False))
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus, name="task_status", native_enum=False))

    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
                                                    index=True)

    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"),
                                                 onupdate=text("now()"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Optimistic concurrency
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    __mapper_args__ = {"version_id_col": version}

    # relationships (optional, if you have User/Project models)
    assignee = relationship("User", lazy="joined")
    project = relationship("Project", lazy="joined")
