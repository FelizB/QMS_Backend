from pydantic import BaseModel


class LookupItemOut(BaseModel):
    id: int
    display_name: str
    color_hex: str | None = None
    sort_order: int
    is_active: bool


class LookupListOut(BaseModel):
    items: list[LookupItemOut]
