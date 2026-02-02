# app/application/validators/file_policy.py
from __future__ import annotations

import re

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_413_REQUEST_ENTITY_TOO_LARGE

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._()+\- ]+")  # conservative allowlist


class FilePolicy:
    """
    Stateless file validation policy:
      - Allowed content types (MIME)
      - Max size in bytes
      - Filename hygiene
    """

    def __init__(self, *, allowed_mime: list[str], max_size_mb: int):
        self.allowed_mime = set(m.lower() for m in allowed_mime or [])
        self.max_size_bytes = int(max_size_mb) * 1024 * 1024

    def sanitize_filename(self, original: str) -> str:
        # Strip control chars and normalize
        name = original.strip().replace("\x00", "")
        # Prevent path traversal: remove separators
        name = name.replace("/", "_").replace("\\", "_").replace("..", ".")
        # Remove suspicious chars
        name = SAFE_NAME_RE.sub("_", name)
        return name or "file"

    def validate_metadata(self, *, filename: str, content_type: str | None) -> None:
        if self.allowed_mime and content_type:
            if content_type.lower() not in self.allowed_mime:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported content type: {content_type}",
                )

    def validate_size(self, *, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Empty file")
        if size_bytes > self.max_size_bytes:
            raise HTTPException(status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
