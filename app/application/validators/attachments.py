# app/application/validators/attachments.py
from __future__ import annotations

from typing import Optional

from app.application.services.file_upload_rules import RulesService


class AttachmentTargetsValidator:
    """
    Validates the target entities for an attachment (project / test_case / test_step)
    using RulesService. Keeps route/use-case clean.
    """

    def __init__(self, rules: RulesService):
        self.rules = rules

    async def __call__(self, *, project_id: int, test_case_id: Optional[int], test_step_id: Optional[int]) -> None:
        await self.rules.validate_attachment_targets(
            project_id=project_id,
            test_case_id=test_case_id,
            test_step_id=test_step_id,
        )
