import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fr_harness.models import Action, ApprovalDecision, Task, TaskStatus
from fr_harness.security import redact_value


@dataclass(frozen=True)
class ApprovalRecord:
    id: UUID
    task_id: UUID
    action: Action
    decision: ApprovalDecision
    created_at: str


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

    def create_approval(self, task_id: UUID, action: Action) -> ApprovalRecord:
        approval_id = uuid4()
        action_payload = redact_value(action.model_dump(mode="json"))
        action_json = json.dumps(action_payload, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approvals (id, task_id, action_json, decision)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(approval_id),
                    str(task_id),
                    action_json,
                    ApprovalDecision.PENDING.value,
                ),
            )
            connection.execute(
                "INSERT INTO events (task_id, kind, payload) VALUES (?, ?, ?)",
                (
                    str(task_id),
                    "approval_requested",
                    json.dumps(
                        {"approval_id": str(approval_id), "action": action_payload},
                        sort_keys=True,
                    ),
                ),
            )
        return self.get_approval(approval_id)

    def get_approval(self, approval_id: UUID) -> ApprovalRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, task_id, action_json, decision, created_at
                FROM approvals
                WHERE id = ?
                """,
                (str(approval_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown approval: {approval_id}")
        return self._approval_from_row(row)

    def get_pending_approval(self, task_id: UUID) -> ApprovalRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, task_id, action_json, decision, created_at
                FROM approvals
                WHERE task_id = ? AND decision = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (str(task_id), ApprovalDecision.PENDING.value),
            ).fetchone()
        return self._approval_from_row(row) if row is not None else None

    def get_latest_approval(self, task_id: UUID) -> ApprovalRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, task_id, action_json, decision, created_at
                FROM approvals
                WHERE task_id = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (str(task_id),),
            ).fetchone()
        return self._approval_from_row(row) if row is not None else None

    def list_pending_approvals(self) -> list[ApprovalRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, task_id, action_json, decision, created_at
                FROM approvals
                WHERE decision = ?
                ORDER BY rowid ASC
                """,
                (ApprovalDecision.PENDING.value,),
            ).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def decide_approval(
        self, approval_id: UUID, decision: ApprovalDecision
    ) -> ApprovalRecord:
        if decision not in {ApprovalDecision.APPROVED, ApprovalDecision.REJECTED}:
            raise ValueError("decision must be approved or rejected")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT task_id, decision FROM approvals WHERE id = ?",
                (str(approval_id),),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown approval: {approval_id}")
            if row["decision"] != ApprovalDecision.PENDING.value:
                raise ValueError(f"approval is no longer pending: {approval_id}")
            cursor = connection.execute(
                """
                UPDATE approvals
                SET decision = ?
                WHERE id = ? AND decision = ?
                """,
                (
                    decision.value,
                    str(approval_id),
                    ApprovalDecision.PENDING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"approval is no longer pending: {approval_id}")
            connection.execute(
                "INSERT INTO events (task_id, kind, payload) VALUES (?, ?, ?)",
                (
                    row["task_id"],
                    "approval_decided",
                    json.dumps(
                        {"approval_id": str(approval_id), "decision": decision.value},
                        sort_keys=True,
                    ),
                ),
            )
        return self.get_approval(approval_id)

    def consume_approval(self, approval_id: UUID) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT task_id FROM approvals WHERE id = ?",
                (str(approval_id),),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown approval: {approval_id}")
            cursor = connection.execute(
                """
                UPDATE approvals
                SET decision = ?
                WHERE id = ? AND decision = ?
                """,
                (
                    ApprovalDecision.CONSUMED.value,
                    str(approval_id),
                    ApprovalDecision.APPROVED.value,
                ),
            )
            if cursor.rowcount == 1:
                connection.execute(
                    "INSERT INTO events (task_id, kind, payload) VALUES (?, ?, ?)",
                    (
                        row["task_id"],
                        "approval_consumed",
                        json.dumps({"approval_id": str(approval_id)}, sort_keys=True),
                    ),
                )
                return True
        return False

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> ApprovalRecord:
        return ApprovalRecord(
            id=UUID(row["id"]),
            task_id=UUID(row["task_id"]),
            action=Action.model_validate_json(row["action_json"]),
            decision=ApprovalDecision(row["decision"]),
            created_at=row["created_at"],
        )
