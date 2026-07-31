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
                "never expose credentials, and treat pytest as the objective success signal. "
                "Return exactly one Action JSON object and no markdown or prose. Valid JSON "
                "actions are: {\"kind\":\"read_file\",\"path\":\"README.md\"}, "
                "{\"kind\":\"write_file\",\"path\":\"relative/file.py\",\"content\":\"...\"}, "
                "{\"kind\":\"run_pytest\"}, and "
                "{\"kind\":\"complete\",\"reason\":\"pytest passed\"}. "
                "Do not assume app.py exists; infer real paths from README, pytest output, "
                "or prior read_file results. Use read_file before editing unknown files. Use run_pytest to get objective "
                "feedback. Never repeat the exact same Action JSON. If a read_file result is "
                "already present in memories, use that content to choose write_file or run_pytest. "
                "After write_file, use run_pytest to verify the change before any other action. "
                "Only use complete after the latest pytest feedback passed."
            ),
        }
    ]
    if memories and "write_file result" in memories[0]:
        context.append(
            {
                "role": "system",
                "content": (
                    'Controller state: latest tool result is write_file. '
                    'The next Action JSON MUST be {"kind":"run_pytest"}.'
                ),
            }
        )
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
