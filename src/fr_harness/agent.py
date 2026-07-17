from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID
from uuid import uuid4

from fr_harness.db import Database
from fr_harness.guardrails import GuardDecision, classify
from fr_harness.llm import LLMClient
from fr_harness.memory import MemoryStore, build_context, redact_secrets
from fr_harness.models import Action, ActionKind, Feedback, Task, TaskStatus
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
            task.status = TaskStatus.PENDING_APPROVAL
            self.database.update_task(task)
            self.database.append_event(
                task.id,
                "approval_requested",
                {
                    "approval_id": str(uuid4()),
                    "action": action_payload,
                    "reason": redact_secrets(action.reason or "dangerous action"),
                },
            )
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

    def run_until_stopped(self, task_id: UUID) -> Task:
        while True:
            task = self.run_once(task_id)
            if task.status in TERMINAL_STATUSES or task.status is TaskStatus.PENDING_APPROVAL:
                return task

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
    def _safe_payload(cls, value: Any) -> Any:
        if isinstance(value, str):
            return redact_secrets(value)
        if isinstance(value, dict):
            return {str(key): cls._safe_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._safe_payload(item) for item in value]
        return value
