from pathlib import Path

import pytest

from fr_harness.db import Database
from fr_harness.llm import MockLLM
from fr_harness.models import Action, ActionKind, ApprovalDecision, TaskStatus
from fr_harness.task_service import TaskService


def make_service(
    tmp_path: Path, actions: list[Action]
) -> tuple[Database, TaskService]:
    database = Database(tmp_path / "service.sqlite3")
    database.initialize()
    return database, TaskService(database, MockLLM(actions))


def passing_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )
    return workspace


def test_create_task_persists_scoped_pytest_permission(tmp_path: Path) -> None:
    database, service = make_service(tmp_path, [])
    workspace = passing_workspace(tmp_path)

    task = service.create_task("repair", workspace, allow_pytest=True)

    assert task.pytest_allowed is True
    assert database.get_task(task.id).pytest_allowed is True


def test_authorized_pytest_runs_without_action_approval(tmp_path: Path) -> None:
    database, service = make_service(
        tmp_path,
        [
            Action(kind=ActionKind.RUN_PYTEST),
            Action(kind=ActionKind.COMPLETE, reason="tests passed"),
        ],
    )
    task = service.create_task(
        "verify project", passing_workspace(tmp_path), allow_pytest=True
    )

    result = service.run(task.id)

    assert result.status is TaskStatus.SUCCEEDED
    assert not any(
        event["kind"] == "approval_requested"
        for event in database.list_events(task.id)
    )


def test_existing_file_write_still_requires_one_action_approval(tmp_path: Path) -> None:
    database, service = make_service(
        tmp_path,
        [
            Action(kind=ActionKind.WRITE_FILE, path="app.py", content="value = 2\n"),
            Action(kind=ActionKind.RUN_PYTEST),
            Action(kind=ActionKind.COMPLETE, reason="tests passed"),
        ],
    )
    workspace = passing_workspace(tmp_path)
    (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
    task = service.create_task("change value", workspace, allow_pytest=True)
    approvals: list[ActionKind] = []

    def approve(task, approval):
        del task
        approvals.append(approval.action.kind)
        return ApprovalDecision.APPROVED

    result = service.run(task.id, approve=approve)

    assert result.status is TaskStatus.SUCCEEDED
    assert approvals == [ActionKind.WRITE_FILE]
    assert (workspace / "app.py").read_text(encoding="utf-8") == "value = 2\n"


def test_service_emits_new_audit_events_as_progress(tmp_path: Path) -> None:
    _, service = make_service(
        tmp_path,
        [
            Action(kind=ActionKind.READ_FILE, path="README.md"),
            Action(kind=ActionKind.RUN_PYTEST),
            Action(kind=ActionKind.COMPLETE, reason="tests passed"),
        ],
    )
    workspace = passing_workspace(tmp_path)
    (workspace / "README.md").write_text("project rules", encoding="utf-8")
    task = service.create_task("inspect", workspace, allow_pytest=True)
    observed: list[str] = []

    service.run(
        task.id,
        on_events=lambda task, events: observed.extend(
            str(event["kind"]) for event in events
        ),
    )

    assert "action" in observed
    assert "tool_result" in observed
    assert "completed" in observed


def test_paused_task_can_resume_but_terminal_task_cannot(tmp_path: Path) -> None:
    database, service = make_service(
        tmp_path,
        [
            Action(kind=ActionKind.RUN_PYTEST),
            Action(kind=ActionKind.COMPLETE, reason="tests passed"),
        ],
    )
    task = service.create_task(
        "resume", passing_workspace(tmp_path), allow_pytest=True
    )
    task.status = TaskStatus.PAUSED
    database.update_task(task)

    result = service.resume(task.id)

    assert result.status is TaskStatus.SUCCEEDED
    with pytest.raises(ValueError, match="cannot be resumed"):
        service.resume(task.id)
