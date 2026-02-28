from pydantic import BaseModel, ConfigDict, field_validator
from typing import List


class UserSkillIn(BaseModel):
    name: str
    percent: int

    @field_validator("percent")
    @classmethod
    def percent_range(cls, v: int):
        if not 0 <= v <= 100:
            raise ValueError("percent must be between 0 and 100")
        return v


class UserSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # <-- IMPORTANT for ORM instances
    id: int
    name: str
    percent: int


class BulkSkillsIn(BaseModel):
    skills: List[UserSkillIn]


class BulkSkillsResult(BaseModel):
    created: List[UserSkillOut]
    skipped_duplicates: List[str]


class DeleteResponse(BaseModel):
    message: str
