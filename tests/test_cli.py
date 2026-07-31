import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from fr_harness import cli
from fr_harness.models import Action, ActionKind


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


class FakeCredentialStore:
    def __init__(self, existing: str | None = None) -> None:
        self.value = existing
        self.set_values: list[str] = []

    def get(self) -> str | None:
        return self.value

    def set(self, value: str) -> None:
        self.value = value
        self.set_values.append(value)

    def clear(self) -> bool:
        was_present = self.value is not None
        self.value = None
        return was_present


def test_setup_writes_provider_env_initializes_database_and_starts_new_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompts: list[str] = []
    answers = iter(["", "", "", "new-secret"])
    launched: dict[str, object] = {}

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    def fake_hidden(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    class FakeLLM:
        def __init__(self, base_url: str, model: str, api_key: str) -> None:
            launched["doctor_base_url"] = base_url
            launched["doctor_model"] = model
            launched["doctor_key"] = api_key

        def next_action(self, context: list[dict[str, str]]) -> Action:
            launched["doctor_context"] = context
            return Action(kind=ActionKind.RUN_PYTEST)

    def fake_start(host: str, port: int) -> bool:
        launched["host"] = host
        launched["port"] = port
        return True

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_prompt", fake_input)
    monkeypatch.setattr(cli, "_hidden_input", fake_hidden)
    monkeypatch.setattr(cli, "OpenAICompatibleLLM", FakeLLM)
    monkeypatch.setattr(cli, "_start_server_in_new_terminal", fake_start)
    monkeypatch.setattr(cli, "_is_port_available", lambda host, port: port != 8000)

    exit_code = cli.main(["setup"], credential_store=FakeCredentialStore())

    assert exit_code == 0
    assert "FR_LLM_BASE_URL=https://api.deepseek.com" in (tmp_path / ".env").read_text(encoding="utf-8")
    assert "FR_LLM_MODEL=deepseek-v4-flash" in (tmp_path / ".env").read_text(encoding="utf-8")
    assert (tmp_path / "fr_harness.sqlite3").exists()
    assert launched["doctor_base_url"] == "https://api.deepseek.com"
    assert launched["doctor_model"] == "deepseek-v4-flash"
    assert launched["doctor_key"] == "new-secret"
    assert launched["host"] == "127.0.0.1"
    assert launched["port"] == 8001
    output = capsys.readouterr().out
    assert "http://127.0.0.1:8001/" in output
    assert "new-secret" not in output


def test_start_server_new_terminal_uses_powershell_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched: dict[str, object] = {}

    def fake_popen(command: list[str], **kwargs: object) -> object:
        launched["command"] = command
        launched.update(kwargs)
        return object()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.os, "name", "nt")
    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    assert cli._start_server_in_new_terminal("127.0.0.1", 8000) is True

    command = launched["command"]
    assert isinstance(command, list)
    assert command[:3] == ["powershell.exe", "-NoExit", "-Command"]
    assert "cd /d" not in command[3]
    assert str(tmp_path) not in command[3]
    assert launched["cwd"] == str(tmp_path)


def test_setup_existing_env_and_keyring_can_decline_overwrite_or_key_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text(
        "CUSTOM=value\nFR_LLM_BASE_URL=https://old.example/v1\nFR_LLM_MODEL=old-model\n",
        encoding="utf-8",
    )
    answers = iter(["", "", "", "n", "n"])

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_prompt", lambda prompt: next(answers))
    monkeypatch.setattr(cli, "_start_server_in_new_terminal", lambda host, port: True)
    monkeypatch.setattr(cli, "_run_doctor", lambda store: 0)
    monkeypatch.setattr(cli, "_is_port_available", lambda host, port: True)

    store = FakeCredentialStore(existing="old-secret")

    exit_code = cli.main(["setup"], credential_store=store)

    assert exit_code == 0
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "CUSTOM=value" in env_text
    assert "FR_LLM_BASE_URL=https://old.example/v1" in env_text
    assert "FR_LLM_MODEL=old-model" in env_text
    assert store.set_values == []


def test_doctor_reports_invalid_base_url_without_printing_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / ".env").write_text(
        "FR_LLM_BASE_URL=api.deepseek.com\nFR_LLM_MODEL=deepseek-v4-flash\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FR_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("FR_LLM_MODEL", raising=False)

    exit_code = cli.main(["doctor"], credential_store=FakeCredentialStore("secret"))

    assert exit_code == 2
    output = capsys.readouterr().out
    assert "缺少 http:// 或 https://" in output
    assert "secret" not in output


def test_doctor_checks_action_json_with_configured_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / ".env").write_text(
        "FR_LLM_BASE_URL=https://api.deepseek.com\nFR_LLM_MODEL=deepseek-v4-flash\n",
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    class FakeLLM:
        def __init__(self, base_url: str, model: str, api_key: str) -> None:
            observed.update(base_url=base_url, model=model, api_key=api_key)

        def next_action(self, context: list[dict[str, str]]) -> Action:
            observed["context"] = context
            return Action(kind=ActionKind.RUN_PYTEST)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "OpenAICompatibleLLM", FakeLLM)
    monkeypatch.delenv("FR_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("FR_LLM_MODEL", raising=False)

    exit_code = cli.main(["doctor"], credential_store=FakeCredentialStore("secret"))

    assert exit_code == 0
    assert observed["base_url"] == "https://api.deepseek.com"
    assert observed["model"] == "deepseek-v4-flash"
    assert observed["api_key"] == "secret"
    output = capsys.readouterr().out
    assert "Action JSON：OK" in output
    assert "secret" not in output


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


def test_windows_quick_start_script_is_relative_and_safe() -> None:
    script = (ROOT / "启动 FR-Harness.cmd").read_text(encoding="utf-8")

    assert "%~dp0" in script
    assert ".venv\\Scripts\\python.exe" in script
    assert "-m fr_harness.cli serve --host 127.0.0.1 --port 8000" in script
    assert "-m fr_harness.cli setup" in script
    assert "D:\\" not in script
    assert "C:\\" not in script
    assert "SchoolProject" not in script
    assert "OPENAI_API_KEY=" not in script
    assert "sk-" not in script

