import subprocess
import sys
from pathlib import Path

from fr_harness.feedback import parse_pytest_result
from fr_harness.guardrails import resolve_workspace_path
from fr_harness.models import Action, ActionKind, ToolResult


class ToolDispatcher:
    def execute(self, action: Action, workspace: Path) -> ToolResult:
        root = workspace.resolve()

        if action.kind is ActionKind.READ_FILE:
            target = self._target(root, action)
            return ToolResult(ok=True, output=target.read_text(encoding="utf-8"))

        if action.kind is ActionKind.WRITE_FILE:
            target = self._target(root, action)
            if action.content is None:
                raise ValueError("write_file requires content")
            target.write_text(action.content, encoding="utf-8")
            return ToolResult(ok=True, output=f"wrote {action.path}")

        if action.kind is ActionKind.RUN_PYTEST:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
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
            return ToolResult(
                ok=feedback.passed,
                output=feedback.summary,
                feedback=feedback,
            )

        raise ValueError(f"unsupported tool action: {action.kind}")

    @staticmethod
    def _target(workspace: Path, action: Action) -> Path:
        if action.path is None:
            raise ValueError(f"{action.kind} requires path")
        return resolve_workspace_path(workspace, action.path)
