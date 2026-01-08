from xmlrpc.client import Boolean
from sqlalchemy import Column, Integer, String,Boolean, DateTime, text,func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, index=True, nullable=False)
    Email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    Admin    = Column(Boolean, nullable=False, server_default=text("FALSE"))
    Active   = Column(Boolean, nullable=False, server_default=text("TRUE"))
    Approved = Column(Boolean, nullable=False, server_default=text("FALSE"))
    Locked   = Column(Boolean, nullable=False, server_default=text("FALSE"))
    Department = Column(String(255), nullable=False)
    Unit       = Column(String(255), nullable=False)
    FirstName  = Column(String(255), nullable=False)
    MiddleName = Column(String(255), nullable=False)
    LastName   = Column(String(255), nullable=False)
    RssToken   = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


