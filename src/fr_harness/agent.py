from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from fr_harness.db import Database
from fr_harness.guardrails import GuardDecision, classify
from fr_harness.llm import LLMClient
from fr_harness.memory import MemoryStore, build_context
from fr_harness.models import (
    Action,
    ActionKind,
    ApprovalDecision,
    Feedback,
    Task,
    TaskStatus,
)
from fr_harness.security import redact_secrets, redact_value
from fr_harness.tools import ToolDispatcher


Classifier = Callable[[Action, Path], GuardDecision]
TERMINAL_STATUSES = {
    TaskStatus.SUCCEEDED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}


class Agent:
    def __init__(
        self,
        database: Database,
        llm: LLMClient,
        *,
        dispatcher: ToolDispatcher | None = None,
        memory: MemoryStore | None = None,
        classifier: Classifier = classify,
        max_iterations: int = 8,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")
        self.database = database
        self.llm = llm
        self.dispatcher = dispatcher or ToolDispatcher()
        self.memory = memory or MemoryStore(database)
        self.classifier = classifier
        self.max_iterations = max_iterations

    def run_once(self, task_id: UUID) -> Task:
        task = self.database.get_task(task_id)
        if task.status in TERMINAL_STATUSES or task.status is TaskStatus.PENDING_APPROVAL:
            return task
        if task.iteration >= self.max_iterations:
            return self._fail(task, "iteration limit")

        task.status = TaskStatus.RUNNING
        events = self.database.list_events(task.id)
        feedback = self._latest_feedback(events)
        context = build_context(
            task.goal,
            self.memory.relevant(task.id),
            feedback,
        )
        try:
            action = self.llm.next_action(context)
        except Exception as error:
            return self._fail(task, "llm error", error_type=type(error).__name__)

        task.iteration += 1
        action_payload = self._safe_payload(action.model_dump(mode="json"))
        last_action = self._last_payload(events, "action")
        self.database.append_event(task.id, "action", action_payload)
        self.database.update_task(task)

        if last_action == action_payload:
            return self._fail(task, "repeated action")

        try:
            decision = self.classifier(action, task.workspace)
        except Exception as error:
            return self._fail(task, "guardrail error", error_type=type(error).__name__)

        if decision is GuardDecision.BLOCKED:
            return self._fail(task, "blocked by guardrail", event_kind="blocked")

        if (
            decision is GuardDecision.REQUIRES_APPROVAL
            or action.kind is ActionKind.REQUEST_APPROVAL
        ):
            self.database.create_approval(task.id, action)
            task.status = TaskStatus.PENDING_APPROVAL
            self.database.update_task(task)
            return task

        if action.kind is ActionKind.COMPLETE:
            if feedback is None or not feedback.passed:
                return self._fail(task, "pytest has not passed")
            task.status = TaskStatus.SUCCEEDED
            self.database.update_task(task)
            self.database.append_event(
                task.id,
                "completed",
                {"reason": redact_secrets(action.reason or "pytest passed")},
            )
            return task

        return self._execute_tool(task, action)

    def run_until_stopped(self, task_id: UUID) -> Task:
        while True:
            task = self.run_once(task_id)
            if task.status in TERMINAL_STATUSES or task.status is TaskStatus.PENDING_APPROVAL:
                return task

    def resume_after_approval(self, task_id: UUID) -> Task:
        task = self.database.get_task(task_id)
        if task.status is not TaskStatus.PENDING_APPROVAL:
            return task
        approval = self.database.get_latest_approval(task.id)
        if approval is None or approval.decision is ApprovalDecision.PENDING:
            return task
        if approval.decision is ApprovalDecision.REJECTED:
            task.status = TaskStatus.CANCELLED
            self.database.update_task(task)
            self.database.append_event(
                task.id,
                "cancelled",
                {"reason": "approval rejected", "approval_id": str(approval.id)},
            )
            return task
        if not self.database.consume_approval(approval.id):
            return self.database.get_task(task.id)

        task.status = TaskStatus.RUNNING
        self.database.update_task(task)
        if approval.action.kind is ActionKind.REQUEST_APPROVAL:
            self.database.append_event(
                task.id,
                "approval_acknowledged",
                {"approval_id": str(approval.id)},
            )
            return task
        return self._execute_tool(task, approval.action)

    def _execute_tool(self, task: Task, action: Action) -> Task:
        try:
            result = self.dispatcher.execute(action, task.workspace)
        except Exception as error:
            return self._fail(task, "tool error", error_type=type(error).__name__)

        self.database.append_event(
            task.id,
            "tool_result",
            {
                "ok": result.ok,
                "output": redact_secrets(result.output),
                "action_kind": action.kind.value,
            },
        )
        if result.output:
            self.memory.add(task.id, "tool_result", result.output)
        if result.feedback is not None:
            safe_feedback = Feedback(
                passed=result.feedback.passed,
                summary=redact_secrets(result.feedback.summary),
                failed_tests=[redact_secrets(item) for item in result.feedback.failed_tests],
            )
            self.database.append_event(
                task.id,
                "feedback",
                safe_feedback.model_dump(mode="json"),
            )
            self.memory.add(task.id, "pytest_feedback", safe_feedback.summary)
        return self.database.get_task(task.id)

    def _fail(
        self,
        task: Task,
        reason: str,
        *,
        event_kind: str = "stopped",
        error_type: str | None = None,
    ) -> Task:
        task.status = TaskStatus.FAILED
        self.database.update_task(task)
        payload: dict[str, object] = {"reason": reason}
        if error_type is not None:
            payload["error_type"] = error_type
        self.database.append_event(task.id, event_kind, payload)
        return task

    @staticmethod
    def _last_payload(
        events: list[dict[str, object]], kind: str
    ) -> dict[str, object] | None:
        for event in reversed(events):
            if event["kind"] == kind:
                payload = event["payload"]
                if isinstance(payload, dict):
                    return payload
        return None

    @classmethod
    def _latest_feedback(cls, events: list[dict[str, object]]) -> Feedback | None:
        payload = cls._last_payload(events, "feedback")
        return Feedback.model_validate(payload) if payload is not None else None

    @classmethod
    def _safe_payload(cls, value: object) -> dict[str, object]:
        redacted = redact_value(value)
        if not isinstance(redacted, dict):
            raise TypeError("action payload must be a mapping")
        return redacted
