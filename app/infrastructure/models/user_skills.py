from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Integer, UniqueConstraint

from app.infrastructure.models.base import Base


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_skill_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    percent: Mapped[int] = mapped_column(Integer)  # 0..100


# app/infrastructure/models/user.py  (add relationship)
from typing import List
from sqlalchemy.orm import relationship

# ...
skills: Mapped[list["UserSkill"]] = relationship(
    "UserSkill", backref="user", cascade="all, delete-orphan", lazy="selectin"
)
