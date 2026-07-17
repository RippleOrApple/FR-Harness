from fr_harness.models import Action, ActionKind, TaskStatus


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
