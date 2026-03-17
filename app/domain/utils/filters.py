from typing import Any, List


def base_filters(model: Any, org_id: int | None = None) -> List[Any]:
    f: List[Any] = []
    if hasattr(model, "is_deleted"):
        f.append(getattr(model, "is_deleted") == False)
    if org_id is not None and hasattr(model, "org_id"):
        f.append(getattr(model, "org_id") == org_id)
    return f
