from pathlib import Path

from fr_harness.agent import Agent
from fr_harness.db import Database
from fr_harness.guardrails import GuardDecision
from fr_harness.models import Action, ActionKind, TaskStatus


class RecordingLLM:
    def __init__(self, actions: list[Action]) -> None:
        self.actions = list(actions)
        self.contexts: list[list[dict[str, str]]] = []

    def next_action(self, context: list[dict[str, str]]) -> Action:
        self.contexts.append(context)
        if not self.actions:
            raise RuntimeError("action queue exhausted")
        return self.actions.pop(0)


def make_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()
    return database


def allow_all(action: Action, workspace: Path) -> GuardDecision:
    del action, workspace
    return GuardDecision.ALLOWED


def test_agent_repairs_after_pytest_feedback_then_completes(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "test_app.py").write_text(
        "from app import greeting\n\ndef test_greeting():\n    assert greeting() == 'hello'\n",
        encoding="utf-8",
    )
    task = database.create_task("fix greeting", workspace)
    llm = RecordingLLM(
        [
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
            Action(kind=ActionKind.COMPLETE, reason="tests now pass"),
        ]
    )

    result = Agent(database, llm, classifier=allow_all).run_until_stopped(task.id)

    assert result.status is TaskStatus.SUCCEEDED
    assert result.iteration == 5
    feedback_events = [
        event for event in database.list_events(task.id) if event["kind"] == "feedback"
    ]
    assert [event["payload"]["passed"] for event in feedback_events] == [False, True]
    assert any(
        "test_app.py::test_greeting" in message["content"]
        for message in llm.contexts[2]
    )


def test_agent_pauses_dangerous_action_without_executing_it(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    workspace = tmp_path / "project"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("old", encoding="utf-8")
    task = database.create_task("change app", workspace)
    llm = RecordingLLM(
        [Action(kind=ActionKind.WRITE_FILE, path="app.py", content="new")]
    )

    result = Agent(database, llm).run_once(task.id)

    assert result.status is TaskStatus.PENDING_APPROVAL
    assert target.read_text(encoding="utf-8") == "old"
    assert database.list_events(task.id)[-1]["kind"] == "approval_requested"


def test_agent_fails_a_blocked_workspace_escape(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    task = database.create_task("read secret", tmp_path)
    llm = RecordingLLM([Action(kind=ActionKind.READ_FILE, path="../secret.txt")])

    result = Agent(database, llm).run_until_stopped(task.id)

    assert result.status is TaskStatus.FAILED
    assert database.list_events(task.id)[-1]["kind"] == "blocked"


def test_agent_fails_complete_before_a_passing_pytest(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    task = database.create_task("claim done", tmp_path)
    llm = RecordingLLM([Action(kind=ActionKind.COMPLETE, reason="trust me")])

    result = Agent(database, llm).run_until_stopped(task.id)

    assert result.status is TaskStatus.FAILED
    assert database.list_events(task.id)[-1]["payload"]["reason"] == "pytest has not passed"


def test_agent_fails_on_two_consecutive_identical_actions(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    (tmp_path / "app.py").write_text("value = 1", encoding="utf-8")
    task = database.create_task("inspect app", tmp_path)
    action = Action(kind=ActionKind.READ_FILE, path="app.py")
    llm = RecordingLLM([action, action.model_copy()])

    result = Agent(database, llm).run_until_stopped(task.id)

    assert result.status is TaskStatus.FAILED
    assert result.iteration == 2
    assert database.list_events(task.id)[-1]["payload"]["reason"] == "repeated action"


def test_agent_fails_when_iteration_budget_is_exhausted(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    (tmp_path / "a.py").write_text("a = 1", encoding="utf-8")
    (tmp_path / "b.py").write_text("b = 2", encoding="utf-8")
    task = database.create_task("inspect forever", tmp_path)
    llm = RecordingLLM(
        [
            Action(kind=ActionKind.READ_FILE, path="a.py"),
            Action(kind=ActionKind.READ_FILE, path="b.py"),
        ]
    )

    result = Agent(database, llm, max_iterations=2).run_until_stopped(task.id)

    assert result.status is TaskStatus.FAILED
    assert result.iteration == 2
    assert database.list_events(task.id)[-1]["payload"]["reason"] == "iteration limit"


def test_different_secret_values_do_not_look_like_a_repeated_action(
    tmp_path: Path,
) -> None:
    database = make_database(tmp_path)
    task = database.create_task("write rotating token", tmp_path)
    first = "TOKEN=alpha-secret-value"
    second = "TOKEN=beta-secret-value"
    llm = RecordingLLM(
        [
            Action(kind=ActionKind.WRITE_FILE, path="token.txt", content=first),
            Action(kind=ActionKind.WRITE_FILE, path="token.txt", content=second),
        ]
    )
    agent = Agent(database, llm, classifier=allow_all)

    agent.run_once(task.id)
    result = agent.run_once(task.id)

    assert result.status is TaskStatus.RUNNING
    assert (tmp_path / "token.txt").read_text(encoding="utf-8") == second
    serialized_events = repr(database.list_events(task.id))
    assert first not in serialized_events
    assert second not in serialized_events
