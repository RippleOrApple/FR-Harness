from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from fr_harness.agent import Agent
from fr_harness.config import HarnessConfig
from fr_harness.db import ApprovalRecord, Database
from fr_harness.llm import LLMClient
from fr_harness.models import ApprovalDecision, Task, TaskStatus
from fr_harness.tools import ToolDispatcher


ApprovalHandler = Callable[[Task, ApprovalRecord], ApprovalDecision]
EventHandler = Callable[[Task, list[dict[str, object]]], None]


def _ignore_events(task: Task, events: list[dict[str, object]]) -> None:
    del task, events


class TaskService:
    def __init__(
        self,
        database: Database,
        llm: LLMClient,
        *,
        config: HarnessConfig | None = None,
        dispatcher: ToolDispatcher | None = None,
    ) -> None:
        self.database = database
        self.llm = llm
        self.config = config or HarnessConfig()
        self.dispatcher = dispatcher or ToolDispatcher()

    def create_task(self, goal: str, workspace: Path, *, allow_pytest: bool) -> Task:
        task = self.database.create_task(goal, workspace)
        if allow_pytest:
            task = self.database.set_pytest_allowed(task.id, True)
        return task

    def list_tasks(self) -> list[Task]:
        return self.database.list_tasks()

    def run(
        self,
        task_id: UUID,
        *,
        approve: ApprovalHandler | None = None,
        on_events: EventHandler = _ignore_events,
    ) -> Task:
        while True:
            task = self.database.get_task(task_id)
            if task.status is TaskStatus.PENDING_APPROVAL:
                if approve is None:
                    return task
                task = self._resolve_approval(task, approve, on_events)
            else:
                if task.status in {
                    TaskStatus.PAUSED,
                    TaskStatus.SUCCEEDED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                }:
                    return task
                before = len(self.database.list_events(task.id))
                task = self._agent_for(task).run_once(task.id)
                self._emit_since(task, before, on_events)
            if task.status in {
                TaskStatus.PAUSED,
                TaskStatus.SUCCEEDED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                return task

    def resume(
        self,
        task_id: UUID,
        *,
        approve: ApprovalHandler | None = None,
        on_events: EventHandler = _ignore_events,
    ) -> Task:
        task = self.database.get_task(task_id)
        if task.status in {
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            raise ValueError(f"task {task_id} cannot be resumed")
        if task.status in {TaskStatus.PAUSED, TaskStatus.RUNNING}:
            task.status = TaskStatus.CREATED
            self.database.update_task(task)
            self.database.append_event(task.id, "resumed", {"reason": "user resumed task"})
        return self.run(task.id, approve=approve, on_events=on_events)

    def _agent_for(self, task: Task) -> Agent:
        approvals = self.config.approvals.model_copy(
            update={
                "run_pytest": (
                    False if task.pytest_allowed else self.config.approvals.run_pytest
                )
            }
        )
        active_config = self.config.model_copy(update={"approvals": approvals})
        return Agent(
            self.database,
            self.llm,
            dispatcher=self.dispatcher,
            config=active_config,
        )

    def _resolve_approval(
        self,
        task: Task,
        approve: ApprovalHandler,
        on_events: EventHandler,
    ) -> Task:
        approval = self.database.get_pending_approval(task.id)
        if approval is None:
            raise RuntimeError(f"task {task.id} has no pending approval")
        decision = approve(task, approval)
        before = len(self.database.list_events(task.id))
        self.database.decide_approval(approval.id, decision)
        task = self._agent_for(task).resume_after_approval(task.id)
        self._emit_since(task, before, on_events)
        return task

    def _emit_since(
        self,
        task: Task,
        start: int,
        on_events: EventHandler,
    ) -> None:
        events = self.database.list_events(task.id)[start:]
        if events:
            on_events(task, events)
