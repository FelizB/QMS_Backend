# app/infrastructure/repositories/utils/key_maps.py

PROJECT_KEY_MAP = {
    "id": (""), "id": ("id", "project_id"),
}

PORTFOLIO_KEY_MAP = {
    "id": ("id", "portfolio_id"),
    "name": ("name", "portfolio_name"),
    "created_at": ("created_at", "creation_date"),
    "status": ("status", "portfolio_status"),
    "owner_name": ("owner_name", "portfolio_owner_name"),
}

PROGRAM_KEY_MAP = {
    "id": ("id", "program_id"),
    "name": ("name", "program_name"),
    "created_at": ("created_at", "creation_date"),
    "status": ("status", "program_status"),
    "owner_name": ("owner_name", "program_owner_name"),
}

USER_KEY_MAP = {
    "id": ("id", "user_id"),
    "first_name": ("first_name",),
    "last_name": ("last_name",),
    "email": ("email",),
    "created_at": ("created_at", "creation_date"),
    "status": ("status", "user_status"),
}

TESTCASE_KEY_MAP = {
    "id": ("id", "testcase_id"),
    "project_id": ("project_id",),
    "name": ("name", "title"),
    "status": ("status",),
    "created_at": ("created_at", "creation_date"),
    "priority": ("priority",),
    "type": ("type", "case_type"),
}

TESTSTEP_KEY_MAP = {
    "id": ("id", "step_id"),
    "testcase_id": ("testcase_id",),
    "sequence": ("sequence", "order"),
    "action": ("action", "step_action"),
    "expected": ("expected", "expected_result"),
    "status": ("status",),
    "created_at": ("created_at", "creation_date"),
}

# Activity feed → directly stored in ActivityLog; mapping utility below will return canonical keys
FEED_KEY_MAP = {
    "title": ("title",),
    "actor_first_name": ("actor_first_name",),
    "performed_at": ("created_at",),
    "entity_type": ("entity_type",),
    "action": ("action",),
    "entity_id": ("entity_id",),
    "outcome": ("outcome",),  # optional in your schema; can be ignored on response
    "error_type": ("error_type",),  # optional
    "error_message": ("error_message",),  # optional
    "name": ("name", "project_name"),
    "created_at": ("created_at", "creation_date"),
    "status": ("status", "project_status"),
}
