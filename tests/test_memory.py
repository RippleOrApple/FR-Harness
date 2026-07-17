import sqlite3
from pathlib import Path

from fr_harness.db import Database
from fr_harness.memory import MemoryStore, build_context
from fr_harness.models import Feedback


def make_store(tmp_path: Path) -> tuple[Database, MemoryStore]:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()
    return database, MemoryStore(database)


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

