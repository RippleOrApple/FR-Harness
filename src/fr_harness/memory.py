import sqlite3
from contextlib import closing
from uuid import UUID

from fr_harness.db import Database
from fr_harness.models import Feedback
from fr_harness.security import redact_secrets


class MemoryStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def add(self, task_id: UUID, category: str, content: str) -> None:
        safe_category = redact_secrets(category)
        safe_content = redact_secrets(content)
        with closing(sqlite3.connect(self.database.path)) as connection, connection:
            connection.execute(
                """
                INSERT INTO memory_entries (task_id, category, content)
                VALUES (?, ?, ?)
                """,
                (str(task_id), safe_category, safe_content),
            )

    def relevant(self, task_id: UUID, limit: int = 5) -> list[str]:
        if limit < 1:
            return []
        with closing(sqlite3.connect(self.database.path)) as connection, connection:
            rows = connection.execute(
                """
                SELECT content
                FROM memory_entries
                WHERE task_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(task_id), limit),
            ).fetchall()
        return [redact_secrets(row[0]) for row in rows]


def build_context(
    goal: str, memories: list[str], feedback: Feedback | None
) -> list[dict[str, str]]:
    context = [
        {
            "role": "system",
            "content": (
                "Only access files inside the bound workspace. Use only approved tools, "
                "never expose credentials, and treat pytest as the objective success signal."
            ),
        }
    ]
    if memories:
        memory_text = "\n".join(f"- {redact_secrets(item)}" for item in memories)
        context.append(
            {"role": "system", "content": f"Relevant task memories:\n{memory_text}"}
        )
    if feedback is not None:
        failed = ", ".join(feedback.failed_tests) or "none"
        context.append(
            {
                "role": "system",
                "content": redact_secrets(
                    "Latest pytest feedback: "
                    f"passed={feedback.passed}; failed_tests={failed}; "
                    f"summary={feedback.summary}"
                ),
            }
        )
    context.append({"role": "user", "content": redact_secrets(goal)})
    return context
