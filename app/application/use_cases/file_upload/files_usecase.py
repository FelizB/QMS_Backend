# app/application/use_cases/files_usecase.py
from datetime import datetime, timezone

from app.application.services.file_upload_rules import RulesService  # your existing validators
from app.infrastructure.models.file_attachment_model import FileAttachment
from app.infrastructure.repositories.file_upload_repository_sqlalchemy import FileAttachmentRepository


class UploadFileForProject:
    def __init__(self, session):
        self.session = session
        self.repo = FileAttachmentRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, *, project_id: int, filename: str, content_type: str | None,
                       size_bytes: int, storage_backend: str, storage_path: str,
                       checksum_sha256: str | None, uploaded_by: str | None,
                       test_case_id: int | None = None, test_step_id: int | None = None):
        """
        # Ancestor integrity
        await self.rules.ensure_project_active(project_id)
        if test_case_id:
            await self.rules.ensure_test_case_active(test_case_id)
        # (Optional) ensure test_step belongs to test_case and is active
        """
        obj = FileAttachment(
            project_id=project_id,
            test_case_id=test_case_id,
            test_step_id=test_step_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_backend=storage_backend,
            storage_path=storage_path,
            checksum_sha256=checksum_sha256,
            uploaded_by=uploaded_by,
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return await self.repo.create(obj)


class ListFilesForProject:
    def __init__(self, session):
        self.repo = FileAttachmentRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, test_case_id: int | None, test_step_id: int | None):
        await self.rules.ensure_project_active(project_id)
        return await self.repo.list(project_id, test_case_id, test_step_id)


class GetFileForProject:
    def __init__(self, session):
        self.repo = FileAttachmentRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, file_id: int):
        await self.rules.ensure_project_active(project_id)
        return await self.repo.get(project_id, file_id)


class DeleteFileForProject:
    def __init__(self, session):
        self.repo = FileAttachmentRepository(session)
        self.rules = RulesService(session)

    async def __call__(self, project_id: int, file_id: int) -> bool:
        await self.rules.ensure_project_active(project_id)
        return await self.repo.soft_delete(project_id, file_id)
