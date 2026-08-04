import os
import sqlite3
from bisect import insort
from contextlib import closing
from uuid import UUID
from pathlib import Path, PurePosixPath

from fr_harness.db import Database
from fr_harness.models import Feedback
from fr_harness.security import redact_secrets


IGNORED_WORKSPACE_ENTRIES = {
    ".coverage",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
}


def workspace_inventory(root: Path, limit: int = 100) -> list[str]:
    if limit < 1:
        return []
    resolved_root = root.resolve()
    selected_tests: list[str] = []
    selected_other: list[str] = []
    for directory, names, files in os.walk(resolved_root, followlinks=False):
        names[:] = sorted(
            name for name in names if name not in IGNORED_WORKSPACE_ENTRIES
        )
        relative_directory = Path(directory).relative_to(resolved_root)
        for name in sorted(files):
            if name in IGNORED_WORKSPACE_ENTRIES:
                continue
            relative = (relative_directory / name).as_posix()
            selected = selected_tests if _is_pytest_file(relative) else selected_other
            insort(selected, relative)
            if len(selected) > limit:
                selected.pop()
    tests = selected_tests[:limit]
    others = selected_other[: limit - len(tests)]
    return sorted(tests + others)


def _is_pytest_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.endswith("_test.py") or (name.startswith("test_") and name.endswith(".py"))


def has_pytest_files(paths: list[str]) -> bool:
    return any(_is_pytest_file(path) for path in paths)


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
    goal: str,
    memories: list[str],
    feedback: Feedback | None,
    workspace_files: list[str] | None = None,
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
                "Create explicitly requested new files with write_file. Use run_pytest after "
                "the required source and pytest test files are ready. "
                "Only use complete after the latest pytest feedback passed."
            ),
        }
    ]
    if workspace_files is not None:
        if workspace_files:
            inventory = "\n".join(f"- {path}" for path in workspace_files)
            context.append(
                {
                    "role": "system",
                    "content": f"Workspace inventory (relative file paths):\n{inventory}",
                }
            )
        else:
            context.append(
                {
                    "role": "system",
                    "content": (
                        "Workspace inventory: empty. This is a greenfield workspace. "
                        "Use write_file to create source and pytest test files named by the "
                        "goal; do not read guessed files such as README.md or app.py."
                    ),
                }
            )
    if memories and "write_file result" in memories[0]:
        has_tests = workspace_files is None or has_pytest_files(workspace_files)
        if has_tests:
            content = (
                'Controller state: latest tool result is write_file. '
                'The next Action JSON MUST be {"kind":"run_pytest"}.'
            )
        else:
            content = (
                "Controller state: latest tool result is write_file, but no pytest test "
                "files exist. No pytest test files exist. The next Action MUST use "
                "write_file to create a test_*.py or *_test.py file for the goal; do not "
                "rewrite the source file and do not run_pytest yet."
            )
        context.append({"role": "system", "content": content})
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
        summary = feedback.summary.lower()
        if not feedback.passed and (
            "no tests ran" in summary or "collected 0 items" in summary
        ):
            context.append(
                {
                    "role": "system",
                    "content": (
                        "Controller state: pytest collected no tests. The next Action MUST "
                        "use write_file to create a test_*.py or *_test.py file for the goal; "
                        "do not rewrite an existing source file or run_pytest again first."
                    ),
                }
            )
    context.append({"role": "user", "content": redact_secrets(goal)})
    return context
