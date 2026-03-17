from __future__ import annotations
from typing import Any, Dict, Iterable, Mapping, Sequence

from sqlalchemy.sql.expression import select, and_


def resolve_columns(model: Any, key_map: Dict[str, tuple[str, ...]]) -> Dict[str, Any]:
    resolved: Dict[str, Any] = {}
    for key, options in key_map.items():
        for name in options:
            col = getattr(model, name, None)
            if col is not None:
                resolved[key] = col
                break
    return resolved


def label_columns(resolved: Mapping[str, Any]) -> list[Any]:
    return [col.label(key) for key, col in resolved.items()]


def build_select(model: Any, key_map: Dict[str, tuple[str, ...]], filters: Iterable[Any] | None = None):
    resolved = resolve_columns(model, key_map)
    if not resolved:
        raise RuntimeError("No columns resolved for model; check key_map and model fields.")
    stmt = select(*label_columns(resolved))
    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt, resolved  # return resolved so callers can order_by resolved['created_at'] etc.


def rows_to_dicts(rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    return [dict(r) for r in rows]
