import mimetypes
from pathlib import Path as path

from fastapi import APIRouter, Path, Query, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_413_REQUEST_ENTITY_TOO_LARGE

from app.application.services.file_type import validate_file_type
from app.application.use_cases.file_upload.files_usecase import (
    UploadFileForProject, ListFilesForProject, GetFileForProject, DeleteFileForProject
)
from app.core.db import get_session
from app.core.settings import settings
from app.infrastructure.storage.local_storage import LocalStorage

file_router = APIRouter(
    prefix="/api/v1/projects/{project_id}/files",
    tags=["Files"],
)

storage = LocalStorage(settings.FILES_LOCAL_ROOT)


@file_router.post("", summary="Upload a file", status_code=201)
async def upload_file(
        project_id: int = Path(..., gt=0),
        test_case_id: int | None = Form(None),
        test_step_id: int | None = Form(None),
        upload: UploadFile = File(...),
        session: AsyncSession = Depends(get_session),
        # user=Depends(get_current_user),
):
    # Size limit (stream to disk while hashing)
    # NOTE: UploadFile doesn't expose size directly; we stream-read in LocalStorage
    # Enforce allowed types
    validate_file_type(upload)
    content_type = upload.content_type or mimetypes.guess_type(upload.filename)[0]
    if settings.ALLOWED_MIME and content_type not in settings.ALLOWED_MIME:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Unsupported content type: {content_type}")

    # Save to storage
    storage_path, size_bytes, sha256 = await storage.save_upload(project_id, upload.file)

    # Hard size cap (post-check). If you want pre-check, set reverse proxy limits too.
    if size_bytes > settings.MAX_UPLOAD_MB * 1024 * 1024:
        # cleanup file
        try:
            path(storage_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    # (Optional) run antivirus scan here (clamd)
    # if infected: delete file and 400

    usecase = UploadFileForProject(session)
    obj = await usecase(
        project_id=project_id,
        test_case_id=test_case_id,
        test_step_id=test_step_id,
        filename=upload.filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_backend="local",
        storage_path=storage_path,
        checksum_sha256=sha256,
        # uploaded_by=getattr(user, "email", None) or getattr(user, "username", None),
        uploaded_by="User"
    )
    return {
        "id": obj.id,
        "filename": obj.filename,
        "content_type": obj.content_type,
        "size_bytes": obj.size_bytes,
        "checksum_sha256": obj.checksum_sha256,
        "created_at": obj.created_at,
    }


@file_router.get("", summary="List files")
async def list_files(
        project_id: int = Path(..., gt=0),
        test_case_id: int | None = Query(None),
        test_step_id: int | None = Query(None),
        session: AsyncSession = Depends(get_session),
        # user=Depends(get_current_user),
):
    items = await ListFilesForProject(session)(project_id, test_case_id, test_step_id)
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "content_type": f.content_type,
            "size_bytes": f.size_bytes,
            "created_at": f.created_at,
        }
        for f in items
    ]


@file_router.get("/{file_id}", summary="Download a file")
async def download_file(
        project_id: int = Path(..., gt=0),
        file_id: int = Path(..., gt=0),
        session: AsyncSession = Depends(get_session),
        # user=Depends(get_current_user),
):
    obj = await GetFileForProject(session)(project_id, file_id)
    if not obj:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Not found")
    if obj.storage_backend != "local":
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Unsupported backend for direct download")

    path = path(obj.storage_path)
    if not path.exists():
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="File missing")

    def iterfile():
        with path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    media_type = obj.content_type or "application/octet-stream"
    headers = {
        "Content-Disposition": f'attachment; filename="{obj.filename}"'
    }
    return StreamingResponse(iterfile(), media_type=media_type, headers=headers)


@file_router.delete("/{file_id}", summary="Soft-delete a file", status_code=204)
async def delete_file(
        project_id: int = Path(..., gt=0),
        file_id: int = Path(..., gt=0),
        session: AsyncSession = Depends(get_session),
        # user=Depends(get_current_user),
):
    ok = await DeleteFileForProject(session)(project_id, file_id)
    if not ok:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Not found")
    return "deletion successful"
