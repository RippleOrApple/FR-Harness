import os
import subprocess
import sys
import time
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
    assert "write_file completed" in result.output
    assert "next action should be run_pytest" in result.output
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "安全写入"


def test_same_size_python_rewrite_advances_timestamp_cache_key(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("wrong", encoding="utf-8")
    old_mtime = int(time.time()) + 0.25
    target.touch()
    os.utime(target, (old_mtime, old_mtime))

    ToolDispatcher().execute(
        Action(kind=ActionKind.WRITE_FILE, path="app.py", content="hello"), tmp_path
    )

    assert int(target.stat().st_mtime) > int(old_mtime)


def test_file_tool_rejects_path_outside_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        ToolDispatcher().execute(
            Action(kind=ActionKind.READ_FILE, path="../secret.txt"), tmp_path
        )


def test_read_file_reports_missing_file_as_recoverable_feedback(tmp_path: Path) -> None:
    result = ToolDispatcher().execute(
        Action(kind=ActionKind.READ_FILE, path="app.py"), tmp_path
    )

    assert result.ok is False
    assert "read_file failed for app.py" in result.output
    assert "file not found" in result.output
    assert "run_pytest" in result.output


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

    assert observed["command"] == [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    assert observed["cwd"] == tmp_path.resolve()
    assert observed["shell"] is False
    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.failed_tests == ["test_app.py::test_greeting"]


def test_run_pytest_does_not_create_pytest_cache(tmp_path: Path) -> None:
    (tmp_path / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )

    result = ToolDispatcher().execute(Action(kind=ActionKind.RUN_PYTEST), tmp_path)

    assert result.ok is True


def test_frozen_executable_uses_embedded_pytest_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "1 passed", "")

    monkeypatch.setattr("fr_harness.tools.subprocess.run", fake_run)
    monkeypatch.setattr("fr_harness.tools.sys.frozen", True, raising=False)
    monkeypatch.setattr("fr_harness.tools.sys.executable", "FR-Harness.exe")

    result = ToolDispatcher().execute(Action(kind=ActionKind.RUN_PYTEST), tmp_path)

    assert result.ok is True
    assert observed["command"] == ["FR-Harness.exe", "_pytest"]
    assert observed["shell"] is False
    assert not (tmp_path / ".pytest_cache").exists()


def test_run_pytest_keeps_capped_details_separate_from_feedback_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stdout = "A" * 60_000
    stderr = "B" * 60_000

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout, stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = ToolDispatcher().execute(Action(kind=ActionKind.RUN_PYTEST), tmp_path)

    assert result.feedback is not None
    assert len(result.feedback.summary) == 2_000
    assert result.details is not None
    assert len(result.details) == 100_000
    assert result.details.startswith("A" * 100)
    assert result.details.endswith("B" * 100)


def test_dispatcher_rejects_non_tool_action(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported tool action"):
        ToolDispatcher().execute(Action(kind=ActionKind.COMPLETE), tmp_path)
