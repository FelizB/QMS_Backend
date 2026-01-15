
# app/application/schemas/common.py
from pydantic import BaseModel, ConfigDict

def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(p.title() for p in parts[1:])

class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra='ignore')
    def model_dump(self, *args, **kwargs):
        # convenience: always produce camelCase in responses
        kwargs.setdefault("by_alias", True)
        return super().model_dump(*args, **kwargs)