from pydantic import BaseModel
from typing import List


class EnumItemOut(BaseModel):
    key: str
    value: str
    label: str


class EnumListOut(BaseModel):
    items: List[EnumItemOut]
