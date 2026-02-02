import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST


class LocalStorage:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)

    def _project_dir(self, project_id: int) -> Path:
        now = datetime.now(timezone.utc)
        return self.root / "projects" / str(project_id) / f"{now.year:04d}" / f"{now.month:02d}"

    async def save_upload(self, project_id: int, file) -> tuple[str, int, str]:
        """
        Saves file to disk, returns (storage_path, size_bytes, sha256hex).
        `file` is a SpooledTemporaryFile-like object from UploadFile.file.
        """
        dirp = self._project_dir(project_id)
        dirp.mkdir(parents=True, exist_ok=True)
        key = f"{uuid.uuid4().hex}"
        path = dirp / key

        sha256 = hashlib.sha256()
        size = 0
        with path.open("wb") as out:
            while True:
                chunk = file.read(1024 * 1024)
                if not chunk:
                    break
                sha256.update(chunk)
                size += len(chunk)
                out.write(chunk)

        if size == 0:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Empty file")

        return str(path), size, sha256.hexdigest()
