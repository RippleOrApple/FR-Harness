import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from fr_harness import cli


ROOT = Path(__file__).resolve().parents[1]


def test_init_creates_database_without_printing_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "state" / "fr.sqlite3"
    secret = "sk-test-secret-value"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    exit_code = cli.main(["init", "--database", str(database_path)])

    assert exit_code == 0
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"tasks", "events", "approvals", "memory_entries"} <= tables
    output = capsys.readouterr().out
    assert secret not in output
    assert "OPENAI_API_KEY" not in output


def test_serve_reads_environment_without_echoing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}
    secret = "sk-test-secret-value"
    monkeypatch.setenv("FR_DATABASE_PATH", str(tmp_path / "fr.sqlite3"))
    monkeypatch.setenv("FR_LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("FR_LLM_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    class FakeLLM:
        def __init__(self, base_url: str, model: str, api_key: str) -> None:
            captured.update(base_url=base_url, model=model, api_key=api_key)

    def fake_run(app: object, **kwargs: object) -> None:
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr(cli, "OpenAICompatibleLLM", FakeLLM)
    monkeypatch.setattr(cli.uvicorn, "run", fake_run)

    exit_code = cli.main(["serve", "--host", "127.0.0.1", "--port", "8123"])

    assert exit_code == 0
    assert captured["base_url"] == "https://llm.invalid/v1"
    assert captured["model"] == "test-model"
    assert captured["api_key"] == secret
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8123
    output = capsys.readouterr().out
    assert secret not in output
    assert "https://llm.invalid/v1" not in output


def test_test_command_uses_fixed_pytest_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert cli.main(["test"]) == 0
    assert observed["command"] == [sys.executable, "-m", "pytest", "-v"]
    assert observed["shell"] is False


def test_docker_distribution_files_enforce_safe_defaults() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert '"fr_harness.cli", "serve"' in dockerfile
    for ignored in (".git", ".env", ".venv", "__pycache__", "*.sqlite*", "temp/"):
        assert ignored in dockerignore
    assert "OPENAI_API_KEY=" in env_example
    assert "sk-" not in env_example

