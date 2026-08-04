import os
import subprocess
import sys
from pathlib import Path

from fr_harness.feedback import parse_pytest_result
from fr_harness.guardrails import resolve_workspace_path
from fr_harness.memory import has_pytest_files, workspace_inventory
from fr_harness.models import Action, ActionKind, ToolResult


class ToolDispatcher:
    def execute(self, action: Action, workspace: Path) -> ToolResult:
        root = workspace.resolve()

        if action.kind is ActionKind.READ_FILE:
            target = self._target(root, action)
            if not target.exists():
                if not workspace_inventory(root, limit=1):
                    guidance = (
                        "workspace is empty; use write_file to create source and pytest "
                        "test files named by the goal"
                    )
                else:
                    guidance = (
                        "read README.md, read pytest output, or use run_pytest to "
                        "identify real files"
                    )
                return ToolResult(
                    ok=False,
                    output=(
                        f"read_file failed for {action.path}: file not found; "
                        f"{guidance}"
                    ),
                )
            if target.is_dir():
                return ToolResult(
                    ok=False,
                    output=(
                        f"read_file failed for {action.path}: path is a directory; "
                        "read a specific file such as README.md or use run_pytest"
                    ),
                )
            return ToolResult(ok=True, output=target.read_text(encoding="utf-8"))

        if action.kind is ActionKind.WRITE_FILE:
            target = self._target(root, action)
            if action.content is None:
                raise ValueError("write_file requires content")
            previous_mtime = target.stat().st_mtime if target.exists() else None
            target.write_text(action.content, encoding="utf-8")
            if previous_mtime is not None and target.suffix == ".py":
                current_stat = target.stat()
                if int(current_stat.st_mtime) <= int(previous_mtime):
                    os.utime(
                        target,
                        (current_stat.st_atime, float(int(previous_mtime) + 1)),
                    )
            inventory = workspace_inventory(root)
            if has_pytest_files(inventory):
                guidance = "next action should be run_pytest"
            else:
                guidance = "next action should create a pytest test file with write_file"
            return ToolResult(
                ok=True,
                output=f"write_file completed for {action.path}; {guidance}",
            )

        if action.kind is ActionKind.RUN_PYTEST:
            command = (
                [sys.executable, "_pytest"]
                if getattr(sys, "frozen", False)
                else [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                ]
            )
            completed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                check=False,
            )
            feedback = parse_pytest_result(
                completed.returncode, completed.stdout, completed.stderr
            )
            details = "\n".join(
                part for part in (completed.stdout, completed.stderr) if part
            )[:100_000]
            return ToolResult(
                ok=feedback.passed,
                output=feedback.summary,
                feedback=feedback,
                details=details,
            )

        raise ValueError(f"unsupported tool action: {action.kind}")

    @staticmethod
    def _target(workspace: Path, action: Action) -> Path:
        if action.path is None:
            raise ValueError(f"{action.kind} requires path")
        return resolve_workspace_path(workspace, action.path)
