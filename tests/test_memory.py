import sqlite3
from pathlib import Path

from fr_harness.db import Database
from fr_harness.memory import MemoryStore, build_context, workspace_inventory
from fr_harness.models import Feedback


def make_store(tmp_path: Path) -> tuple[Database, MemoryStore]:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()
    return database, MemoryStore(database)


def test_workspace_inventory_is_bounded_sorted_and_ignores_caches(
    tmp_path: Path,
) -> None:
    (tmp_path / "fibonacci.py").write_text("", encoding="utf-8")
    (tmp_path / "test_fibonacci.py").write_text("", encoding="utf-8")
    for index in range(105):
        (tmp_path / f"module_{index:03}.py").write_text("", encoding="utf-8")
    for ignored in (
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
    ):
        cache = tmp_path / ignored
        cache.mkdir()
        (cache / "secret.py").write_text("", encoding="utf-8")
    (tmp_path / ".coverage").write_text("cache", encoding="utf-8")

    inventory = workspace_inventory(tmp_path)

    assert len(inventory) == 100
    assert inventory == sorted(inventory)
    assert "fibonacci.py" in inventory
    assert "test_fibonacci.py" in inventory
    assert all("secret.py" not in path for path in inventory)
    assert ".coverage" not in inventory


def test_relevant_returns_only_the_two_most_recent_task_memories(tmp_path: Path) -> None:
    database, store = make_store(tmp_path)
    task = database.create_task("fix greeting", tmp_path)
    other = database.create_task("other task", tmp_path)
    store.add(task.id, "failure", "first attempt")
    store.add(task.id, "failure", "second attempt")
    store.add(other.id, "failure", "unrelated attempt")
    store.add(task.id, "convention", "third and newest")

    memories = store.relevant(task.id, limit=2)

    assert memories == ["third and newest", "second attempt"]


def test_build_context_orders_security_memory_feedback_and_goal() -> None:
    feedback = Feedback(
        passed=False,
        summary="FAILED test_app.py::test_greeting - AssertionError",
        failed_tests=["test_app.py::test_greeting"],
    )

    context = build_context(
        "fix greeting",
        ["previous attempt changed the wrong return value"],
        feedback,
    )

    assert [message["role"] for message in context] == [
        "system",
        "system",
        "system",
        "user",
    ]
    assert "workspace" in context[0]["content"].lower()
    assert "previous attempt" in context[1]["content"]
    assert "test_app.py::test_greeting" in context[2]["content"]
    assert context[3] == {"role": "user", "content": "fix greeting"}


def test_build_context_instructs_llm_to_return_action_json() -> None:
    context = build_context("fix greeting", [], None)

    system_prompt = context[0]["content"]
    assert "JSON" in system_prompt
    assert "Action" in system_prompt
    assert "read_file" in system_prompt
    assert "write_file" in system_prompt
    assert "run_pytest" in system_prompt
    assert '{"kind":"read_file","path":"README.md"}' in system_prompt
    assert "Do not assume app.py exists" in system_prompt
    assert "Never repeat" in system_prompt
    assert "write_file or run_pytest" in system_prompt


def test_build_context_describes_an_empty_greenfield_workspace() -> None:
    context = build_context("create fibonacci", [], None, workspace_files=[])

    serialized = "\n".join(message["content"] for message in context)
    assert "Workspace inventory: empty" in serialized
    assert "greenfield workspace" in serialized
    assert "create source and pytest test files" in serialized


def test_build_context_requests_tests_after_source_write_without_test_files() -> None:
    context = build_context(
        "create fibonacci",
        ["write_file result for fibonacci.py: write_file completed for fibonacci.py"],
        None,
        workspace_files=["fibonacci.py"],
    )

    serialized = "\n".join(message["content"] for message in context)
    assert "No pytest test files exist" in serialized
    assert "test_*.py" in serialized
    assert "do not rewrite the source file" in serialized


def test_build_context_runs_pytest_after_write_when_tests_exist() -> None:
    context = build_context(
        "fix greeting",
        ["write_file result for app.py: write_file completed for app.py"],
        None,
        workspace_files=["app.py", "test_app.py"],
    )

    serialized = "\n".join(message["content"] for message in context)
    assert 'latest tool result is write_file' in serialized
    assert '{"kind":"run_pytest"}' in serialized


def test_build_context_requests_test_file_when_pytest_collected_nothing() -> None:
    context = build_context(
        "create fibonacci",
        ["run_pytest result: no tests ran in 0.00s"],
        Feedback(passed=False, summary="no tests ran in 0.00s"),
        workspace_files=["fibonacci.py"],
    )

    serialized = "\n".join(message["content"] for message in context)
    assert "pytest collected no tests" in serialized
    assert "MUST use write_file" in serialized
    assert "test_*.py" in serialized


def test_build_context_promotes_write_file_state_to_controller_instruction() -> None:
    context = build_context(
        "fix greeting",
        ["write_file result for app.py: write_file completed for app.py; next action should be run_pytest"],
        None,
        workspace_files=["app.py", "test_app.py"],
    )

    serialized = "\n".join(message["content"] for message in context)
    assert 'latest tool result is write_file' in serialized
    assert '{"kind":"run_pytest"}' in serialized


def test_memory_and_context_redact_credentials(tmp_path: Path) -> None:
    database, store = make_store(tmp_path)
    task = database.create_task("secure task", tmp_path)
    secret = "sk-test-secret-value"

    store.add(task.id, "failure", f"OPENAI_API_KEY={secret}")
    memories = store.relevant(task.id)
    context = build_context(
        f"do not reveal TOKEN={secret}",
        memories,
        Feedback(passed=False, summary=f"SECRET={secret}"),
    )

    serialized = repr(context)
    assert secret not in serialized
    assert "[REDACTED]" in serialized
    with sqlite3.connect(database.path) as connection:
        stored = connection.execute("SELECT content FROM memory_entries").fetchone()[0]
    assert secret not in stored

