import json
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

from fr_harness.models import Task, TaskStatus


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    status TEXT NOT NULL,
                    iteration INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    action_json TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def create_task(self, goal: str, workspace: Path) -> Task:
        task = Task(id=uuid4(), goal=goal, workspace=workspace.resolve())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (id, goal, workspace, status, iteration)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(task.id), task.goal, str(task.workspace), task.status.value, task.iteration),
            )
        return task

    def get_task(self, task_id: UUID) -> Task:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, goal, workspace, status, iteration FROM tasks WHERE id = ?",
                (str(task_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown task: {task_id}")
        return Task(
            id=UUID(row["id"]),
            goal=row["goal"],
            workspace=Path(row["workspace"]),
            status=TaskStatus(row["status"]),
            iteration=row["iteration"],
        )

    def update_task(self, task: Task) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET goal = ?, workspace = ?, status = ?, iteration = ?
                WHERE id = ?
                """,
                (
                    task.goal,
                    str(task.workspace.resolve()),
                    task.status.value,
                    task.iteration,
                    str(task.id),
                ),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"unknown task: {task.id}")

    def append_event(self, task_id: UUID, kind: str, payload: dict[str, object]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (task_id, kind, payload) VALUES (?, ?, ?)",
                (str(task_id), kind, json.dumps(payload, sort_keys=True)),
            )

    def list_events(self, task_id: UUID) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, kind, payload, created_at FROM events WHERE task_id = ? ORDER BY id ASC",
                (str(task_id),),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "payload": json.loads(row["payload"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
