from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, constr
from app.domain.enum import TaskType, TaskPriority, TaskStatus


# Minimal person object for assignee preview
class Person(BaseModel):
    id: int
    first_name: str
    last_name: str
    avatarUrl: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    title: constr(min_length=1, max_length=300)
    description: Optional[str] = None
    type: TaskType
    priority: TaskPriority
    status: TaskStatus
    assignee_id: Optional[int] = Field(default=None)
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=300)] = None
    description: Optional[str] = None
    type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    assignee_id: Optional[int | None] = None
    due_date: Optional[datetime | None] = None
    version: int | None = Field(default=None, description="Optimistic concurrency version")


class TaskOut(BaseModel):
    id: int
    projectId: int = Field(alias="project_id")
    title: str
    description: Optional[str] = None
    type: TaskType
    priority: TaskPriority
    status: TaskStatus
    assignee: Optional[Person] = None
    dueDate: Optional[datetime] = Field(alias="due_date", default=None)
    createdAt: datetime = Field(alias="created_at")
    updatedAt: Optional[datetime] = Field(alias="updated_at", default=None)
    version: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PagedTasks(BaseModel):
    items: List[TaskOut]
    total: int
    page: int
    pageSize: int = Field(alias="page_size")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
