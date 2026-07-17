from pathlib import Path

import pytest

from fr_harness.guardrails import (
    ApprovalStateMachine,
    GuardDecision,
    classify,
    resolve_workspace_path,
)
from fr_harness.models import Action, ActionKind


def test_workspace_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        resolve_workspace_path(tmp_path, "../secret.txt")


def test_existing_file_write_requires_approval(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("old", encoding="utf-8")

    decision = classify(
        Action(kind=ActionKind.WRITE_FILE, path="app.py", content="new"),
        tmp_path,
    )

    assert decision is GuardDecision.REQUIRES_APPROVAL


def test_new_file_write_is_allowed(tmp_path: Path) -> None:
    decision = classify(
        Action(kind=ActionKind.WRITE_FILE, path="new.py", content="new"),
        tmp_path,
    )

    assert decision is GuardDecision.ALLOWED


def test_pytest_action_requires_approval(tmp_path: Path) -> None:
    assert classify(Action(kind=ActionKind.RUN_PYTEST), tmp_path) is GuardDecision.REQUIRES_APPROVAL


def test_approval_must_be_approved_and_can_be_consumed_once() -> None:
    machine = ApprovalStateMachine()
    approval = machine.create("write_file", "overwrite app.py")

    assert machine.can_execute(approval.id) is False
    machine.approve(approval.id)
    assert machine.can_execute(approval.id) is True
    assert machine.consume(approval.id) is True
    assert machine.can_execute(approval.id) is False
    assert machine.consume(approval.id) is False


def test_rejected_approval_cannot_execute(tmp_path: Path) -> None:
    machine = ApprovalStateMachine()
    approval = machine.create("run_pytest", "run tests")

    machine.reject(approval.id)

    assert machine.can_execute(approval.id) is False
