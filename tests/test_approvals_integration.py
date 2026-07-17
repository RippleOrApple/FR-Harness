import sqlite3
from pathlib import Path

from fr_harness.agent import Agent
from fr_harness.db import Database
from fr_harness.llm import MockLLM
from fr_harness.models import Action, ActionKind, ApprovalDecision, TaskStatus


def make_database(path: Path) -> Database:
    database = Database(path)
    database.initialize()
    return database


def request_overwrite(database: Database, workspace: Path) -> tuple[object, object]:
    task = database.create_task("replace app", workspace)
    action = Action(kind=ActionKind.WRITE_FILE, path="app.py", content="new")
    result = Agent(database, MockLLM([action])).run_once(task.id)
    return task, result


def test_approved_overwrite_resumes_once_after_database_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "fr.sqlite3"
    workspace = tmp_path / "project"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("old", encoding="utf-8")
    database = make_database(database_path)
    task, paused = request_overwrite(database, workspace)

    assert paused.status is TaskStatus.PENDING_APPROVAL
    assert target.read_text(encoding="utf-8") == "old"

    restarted = make_database(database_path)
    pending = restarted.get_pending_approval(task.id)
    assert pending is not None
    assert pending.action == Action(
        kind=ActionKind.WRITE_FILE, path="app.py", content="new"
    )
    restarted.decide_approval(pending.id, ApprovalDecision.APPROVED)

    resumed = Agent(restarted, MockLLM([])).resume_after_approval(task.id)

    assert resumed.status is TaskStatus.RUNNING
    assert target.read_text(encoding="utf-8") == "new"
    assert restarted.get_approval(pending.id).decision is ApprovalDecision.CONSUMED

    target.write_text("changed after first execution", encoding="utf-8")
    Agent(restarted, MockLLM([])).resume_after_approval(task.id)
    assert target.read_text(encoding="utf-8") == "changed after first execution"
    event_kinds = [event["kind"] for event in restarted.list_events(task.id)]
    assert "approval_decided" in event_kinds
    assert event_kinds.count("approval_consumed") == 1


def test_rejected_overwrite_cancels_without_execution(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("old", encoding="utf-8")
    database = make_database(tmp_path / "fr.sqlite3")
    task, _ = request_overwrite(database, workspace)
    pending = database.get_pending_approval(task.id)
    assert pending is not None

    database.decide_approval(pending.id, ApprovalDecision.REJECTED)
    result = Agent(database, MockLLM([])).resume_after_approval(task.id)

    assert result.status is TaskStatus.CANCELLED
    assert target.read_text(encoding="utf-8") == "old"
    assert database.get_approval(pending.id).decision is ApprovalDecision.REJECTED


def test_approval_consume_compare_and_set_succeeds_only_once(tmp_path: Path) -> None:
    database = make_database(tmp_path / "fr.sqlite3")
    task = database.create_task("run tests", tmp_path)
    approval = database.create_approval(
        task.id, Action(kind=ActionKind.RUN_PYTEST, reason="verify")
    )
    database.decide_approval(approval.id, ApprovalDecision.APPROVED)

    assert database.consume_approval(approval.id) is True
    assert database.consume_approval(approval.id) is False


def test_persisted_approval_redacts_credentials(tmp_path: Path) -> None:
    database = make_database(tmp_path / "fr.sqlite3")
    task = database.create_task("safe write", tmp_path)
    secret = "sk-test-secret-value"

    approval = database.create_approval(
        task.id,
        Action(
            kind=ActionKind.WRITE_FILE,
            path="config.py",
            content=f"OPENAI_API_KEY={secret}",
        ),
    )

    assert secret not in (approval.action.content or "")
    with sqlite3.connect(database.path) as connection:
        action_json = connection.execute(
            "SELECT action_json FROM approvals WHERE id = ?", (str(approval.id),)
        ).fetchone()[0]
    assert secret not in action_json
    assert "[REDACTED]" in action_json

