from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from fr_harness.agent import Agent
from fr_harness.db import Database
from fr_harness.guardrails import GuardDecision
from fr_harness.llm import MockLLM
from fr_harness.models import (
    Action,
    ActionKind,
    ApprovalDecision,
    Feedback,
    TaskStatus,
    ToolResult,
)
from fr_harness.task_service import TaskService
from fr_harness.tools import ToolDispatcher


class DeterministicDemoDispatcher(ToolDispatcher):
    def __init__(self, pytest_results: list[bool]) -> None:
        self.pytest_results = iter(pytest_results)
        self.pytest_calls = 0

    def execute(self, action: Action, workspace: Path) -> ToolResult:
        if action.kind is not ActionKind.RUN_PYTEST:
            return super().execute(action, workspace)
        self.pytest_calls += 1
        passed = next(self.pytest_results)
        summary = "1 passed" if passed else "FAILED test_app.py::test_greeting"
        return ToolResult(
            ok=passed,
            output=summary,
            feedback=Feedback(
                passed=passed,
                summary=summary,
                failed_tests=[] if passed else ["test_app.py::test_greeting"],
            ),
            details=summary,
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

        def approved_action(action: Action, bound_workspace: Path) -> GuardDecision:
            del action, bound_workspace
            return GuardDecision.ALLOWED

        result = Agent(
            database,
            MockLLM(actions),
            classifier=approved_action,
            dispatcher=DeterministicDemoDispatcher([False, True]),
        ).run_until_stopped(task.id)
        feedback = [
            event["payload"]
            for event in database.list_events(task.id)
            if event["kind"] == "feedback"
        ]
        return result.status is TaskStatus.SUCCEEDED and [
            item["passed"] for item in feedback
        ] == [False, True]


def _task_pytest_permission_check() -> bool:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "project"
        workspace.mkdir()
        (workspace / "test_demo.py").write_text(
            "def test_demo():\n    assert 2 + 2 == 4\n",
            encoding="utf-8",
        )
        database = _database(root)
        dispatcher = DeterministicDemoDispatcher([True])
        service = TaskService(
            database,
            MockLLM(
                [
                    Action(kind=ActionKind.RUN_PYTEST),
                    Action(kind=ActionKind.COMPLETE, reason="pytest passed"),
                ]
            ),
            dispatcher=dispatcher,
        )
        task = service.create_task("run tests", workspace, allow_pytest=True)
        result = service.run(task.id)
        return result.status is TaskStatus.SUCCEEDED and dispatcher.pytest_calls == 1


def run_demo() -> int:
    if hasattr(sys.stdout, "reconfigure") and not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8")
    guardrail_passed, one_time_passed = _approval_checks()
    feedback_passed = _feedback_repair_check()
    pytest_permission_passed = _task_pytest_permission_check()
    checks = [
        ("危险操作审批", guardrail_passed),
        ("失败反馈纠错", feedback_passed),
        ("一次性文件审批", one_time_passed),
        ("任务级 pytest 权限", pytest_permission_passed),
    ]
    for label, passed in checks:
        print(f"{label}：{'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


def main() -> None:
    raise SystemExit(run_demo())


if __name__ == "__main__":
    main()
