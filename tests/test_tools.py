import subprocess
import sys
from pathlib import Path

import pytest

from fr_harness.models import Action, ActionKind
from fr_harness.tools import ToolDispatcher


def test_read_file_returns_utf8_content(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("你好，Harness", encoding="utf-8")

    result = ToolDispatcher().execute(
        Action(kind=ActionKind.READ_FILE, path="hello.txt"), tmp_path
    )

    assert result.ok is True
    assert result.output == "你好，Harness"


def test_write_file_writes_utf8_content(tmp_path: Path) -> None:
    result = ToolDispatcher().execute(
        Action(kind=ActionKind.WRITE_FILE, path="hello.txt", content="安全写入"),
        tmp_path,
    )

    assert result.ok is True
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "安全写入"


def test_file_tool_rejects_path_outside_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        ToolDispatcher().execute(
            Action(kind=ActionKind.READ_FILE, path="../secret.txt"), tmp_path
        )


def test_run_pytest_uses_fixed_command_and_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 1, "FAILED test_app.py::test_greeting\n", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = ToolDispatcher().execute(Action(kind=ActionKind.RUN_PYTEST), tmp_path)

    assert observed["command"] == [sys.executable, "-m", "pytest", "-q"]
    assert observed["cwd"] == tmp_path.resolve()
    assert observed["shell"] is False
    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.failed_tests == ["test_app.py::test_greeting"]


def test_dispatcher_rejects_non_tool_action(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported tool action"):
        ToolDispatcher().execute(Action(kind=ActionKind.COMPLETE), tmp_path)

