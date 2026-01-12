from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, func,text
from sqlalchemy.orm import declarative_base
from .base import Base
import sqlalchemy as sa

class Project(Base):
    __tablename__ = "projects"

    # Keys / Ids
    ProjectId = Column(Integer, primary_key=True, index=True)
    ProjectTemplateId = Column(Integer, nullable=True, index=True)
    ProjectGroupId = Column(Integer, nullable=True, index=True)

    # Basic info
    Name = Column(String(255), nullable=False, index=True)
    Description = Column(Text, nullable=True)
    Website = Column(String(2048), nullable=True)

    # Dates / status
    CreationDate = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    Active = Column(Boolean, nullable=False, server_default=sa.sql.true())
    WorkingHours = Column(Integer, nullable=False, index=True)

    # Planning fields
    WorkingHours = Column(Integer, nullable=True)
    WorkingDays = Column(Integer, nullable=True)
    NonWorkingHours = Column(Integer, nullable=True)
    StartDate = Column(Date, nullable=True)
    EndDate = Column(Date, nullable=True)
    PercentComplete = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, nullable=False, server_default=sa.sql.false())
    is_active = Column(Boolean, nullable=False, server_default=sa.sql.true())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
