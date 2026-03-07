from enum import Enum


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
