from uuid import uuid4

from fr_harness.models import Action, ActionKind, Task, TaskStatus


def test_action_keeps_write_file_payload() -> None:
    action = Action(
        kind=ActionKind.WRITE_FILE,
        path="app.py",
        content="print('ok')",
    )

    assert action.path == "app.py"
    assert action.content == "print('ok')"


def test_task_status_has_pending_approval() -> None:
    assert TaskStatus.PENDING_APPROVAL.value == "pending_approval"


def test_task_supports_paused_status_and_scoped_pytest_permission(tmp_path) -> None:
    task = Task(
        id=uuid4(),
        goal="repair",
        workspace=tmp_path,
        status=TaskStatus.PAUSED,
    )

    assert task.status is TaskStatus.PAUSED
    assert task.pytest_allowed is False
