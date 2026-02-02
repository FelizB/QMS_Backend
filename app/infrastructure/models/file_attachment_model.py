from datetime import datetime, timezone

from sqlalchemy import Integer, String, ForeignKey, Boolean, DateTime, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.infrastructure.models.base import Base


class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id", ondelete="RESTRICT"), index=True)
    test_case_id: Mapped[int | None] = mapped_column(ForeignKey("test_cases.id", ondelete="RESTRICT"), nullable=True,
                                                     index=True)
    test_step_id: Mapped[int | None] = mapped_column(ForeignKey("test_steps.id", ondelete="RESTRICT"), nullable=True,
                                                     index=True)

    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_backend: Mapped[str] = mapped_column(String(16), default="local")  # local|s3
    storage_path: Mapped[str] = mapped_column(String(2048))  # local path or S3 key
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))
    uploaded_by: Mapped[str | None] = mapped_column(String(256), nullable=True)  # or user_id int FK

    # relationships (optional for eager joins)
    project = relationship("Project")
    test_case = relationship("TestCase")
    test_step = relationship("TestStep")

    __table_args__ = (
        # If you want to ensure exactly one parent is used, enforce at app layer.
        # You can alternatively use a CHECK constraint but it's trickier across nullable FKs.
    )
