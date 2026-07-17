from pathlib import Path
from tempfile import TemporaryDirectory

from fr_harness.agent import Agent
from fr_harness.db import Database
from fr_harness.guardrails import GuardDecision
from fr_harness.llm import MockLLM
from fr_harness.models import (
    Action,
    ActionKind,
    ApprovalDecision,
    TaskStatus,
)


def _database(root: Path) -> Database:
    database = Database(root / "fr.sqlite3")
    database.initialize()
    return database


def _approval_checks() -> tuple[bool, bool]:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "project"
        workspace.mkdir()
        target = workspace / "app.py"
        target.write_text("old", encoding="utf-8")
        database = _database(root)
        task = database.create_task("replace app", workspace)
        action = Action(kind=ActionKind.WRITE_FILE, path="app.py", content="new")

        paused = Agent(database, MockLLM([action])).run_once(task.id)
        guardrail_passed = (
            paused.status is TaskStatus.PENDING_APPROVAL
            and target.read_text(encoding="utf-8") == "old"
        )

        approval = database.get_pending_approval(task.id)
        assert approval is not None
        database.decide_approval(approval.id, ApprovalDecision.APPROVED)
        Agent(database, MockLLM([])).resume_after_approval(task.id)
        first_execution = target.read_text(encoding="utf-8") == "new"

        target.write_text("sentinel", encoding="utf-8")
        Agent(database, MockLLM([])).resume_after_approval(task.id)
        one_time_passed = (
            first_execution
            and target.read_text(encoding="utf-8") == "sentinel"
            and database.get_approval(approval.id).decision
            is ApprovalDecision.CONSUMED
        )
        return guardrail_passed, one_time_passed


def _feedback_repair_check() -> bool:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "project"
        workspace.mkdir()
        (workspace / "test_app.py").write_text(
            "from app import greeting\n\ndef test_greeting():\n    assert greeting() == 'hello'\n",
            encoding="utf-8",
        )
        database = _database(root)
        task = database.create_task("fix greeting", workspace)
        actions = [
            Action(
                kind=ActionKind.WRITE_FILE,
                path="app.py",
                content="def greeting():\n    return 'wrong'\n",
            ),
            Action(kind=ActionKind.RUN_PYTEST),
            Action(
                kind=ActionKind.WRITE_FILE,
                path="app.py",
                content="def greeting():\n    return 'hello'\n",
            ),
            Action(kind=ActionKind.RUN_PYTEST),
            Action(kind=ActionKind.COMPLETE, reason="pytest passed"),
        ]

        def approved_action(
            action: Action, bound_workspace: Path
        ) -> GuardDecision:
            del action, bound_workspace
            return GuardDecision.ALLOWED

        result = Agent(
            database,
            MockLLM(actions),
            classifier=approved_action,
        ).run_until_stopped(task.id)
        feedback = [
            event["payload"]
            for event in database.list_events(task.id)
            if event["kind"] == "feedback"
        ]
        return result.status is TaskStatus.SUCCEEDED and [
            item["passed"] for item in feedback
        ] == [False, True]


def main() -> None:
    guardrail_passed, one_time_passed = _approval_checks()
    feedback_passed = _feedback_repair_check()
    assert guardrail_passed
    assert feedback_passed
    assert one_time_passed
    print("guardrail approval: PASS")
    print("feedback repair: PASS")
    print("approval one-time use: PASS")


if __name__ == "__main__":
    main()
