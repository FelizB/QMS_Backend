from enum import Enum
from enum import StrEnum


class TaskType(str, Enum):
    TASK = "TASK"
    BUG = "BUG"
    FEATURE = "FEATURE"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"


class ProjectStatus(str, Enum):
    PLANNING = "PLANNING"
    DESIGN = "DESIGN"
    EXECUTION = "EXECUTION"
    SIGN_OFF = "SIGN_OFF"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"
    DONE = "DONE"


class EntityType(str, Enum):
    USER = "user"
    PORTFOLIO = "portfolio"
    PROGRAM = "program"
    PROJECT = "project"
    TESTCASE = "testcase"
    TESTSTEP = "teststep"


class ActivityAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    EXECUTED = "executed"


class ActivityOutcome(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class Role(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class RoleAction(str, Enum):
    INITIATE = "INITIATE"
    VIEW = "VIEW"
    REVIEW = "REVIEW"
    APPROVE = "APPROVE"


class EntityType(StrEnum):
    PROJECT = "project"
    PROGRAM = "program"
    PORTFOLIO = "portfolio"
    USER = "user"


class Action(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
