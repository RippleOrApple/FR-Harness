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
