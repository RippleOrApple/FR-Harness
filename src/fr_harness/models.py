from enum import StrEnum
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionKind(StrEnum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    RUN_PYTEST = "run_pytest"
    REQUEST_APPROVAL = "request_approval"
    COMPLETE = "complete"


class ApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Action(BaseModel):
    kind: ActionKind
    path: str | None = None
    content: str | None = None
    reason: str | None = None


class Task(BaseModel):
    id: UUID
    goal: str
    workspace: Path
    status: TaskStatus = TaskStatus.CREATED
    iteration: int = 0


class Feedback(BaseModel):
    passed: bool
    summary: str
    failed_tests: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    ok: bool
    output: str
    feedback: Feedback | None = None
