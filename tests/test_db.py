import sqlite3

from fr_harness.db import Database
from fr_harness.models import TaskStatus


def test_create_task_persists_a_created_task(tmp_path) -> None:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()

    task = database.create_task("fix greeting", tmp_path)

    persisted = database.get_task(task.id)
    assert persisted.status is TaskStatus.CREATED
    assert persisted.goal == "fix greeting"


def test_append_event_preserves_json_payload_in_order(tmp_path) -> None:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()
    task = database.create_task("fix greeting", tmp_path)
    database.append_event(task.id, "action", {"kind": "read_file"})
    database.append_event(task.id, "feedback", {"passed": False})

    events = database.list_events(task.id)

    assert [event["kind"] for event in events] == ["action", "feedback"]
    assert events[0]["payload"] == {"kind": "read_file"}


def test_database_migrates_old_tasks_and_persists_pytest_permission(tmp_path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                workspace TEXT NOT NULL,
                status TEXT NOT NULL,
                iteration INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    database = Database(database_path)
    database.initialize()
    task = database.create_task("repair", tmp_path)

    assert task.pytest_allowed is False
    updated = database.set_pytest_allowed(task.id, True)
    assert updated.pytest_allowed is True
    assert database.get_task(task.id).pytest_allowed is True


def test_database_persists_paused_task_status(tmp_path) -> None:
    database = Database(tmp_path / "tasks.sqlite3")
    database.initialize()
    task = database.create_task("repair", tmp_path)
    task.status = TaskStatus.PAUSED

    database.update_task(task)

    assert database.get_task(task.id).status is TaskStatus.PAUSED
