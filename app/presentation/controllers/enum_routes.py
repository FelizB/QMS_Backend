from fastapi import APIRouter, HTTPException
from app.domain.enum import ProjectStatus, TaskType, TaskPriority, TaskStatus
from app.presentation.schemas.enums_schema import EnumListOut

ENUM_REGISTRY = {
    "project-status": ProjectStatus,
    "task-status": TaskStatus,
    "task-priority": TaskPriority,
    "task-tyoe": TaskType,
}

enums_router = APIRouter(prefix="/api/v1/enums", tags=["enums"])


@enums_router.get("/{enum_name}", response_model=EnumListOut)
async def list_enum(enum_name: str):
    enum_cls = ENUM_REGISTRY.get(enum_name)
    if not enum_cls:
        raise HTTPException(status_code=404, detail="Enum not found")

    return {
        "items": [
            {
                "key": e.name,
                "value": e.value,
                "label": e.value.replace("_", " "),
            }
            for e in enum_cls
        ]
    }
