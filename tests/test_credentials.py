from pathlib import Path

import pytest

from fr_harness import cli
from fr_harness.credentials import (
    ACCOUNT_NAME,
    SERVICE_NAME,
    CredentialStore,
    CredentialStoreError,
    resolve_api_key,
)


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def set_password(
        self, service_name: str, username: str, password: str
    ) -> None:
        self.values[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        del self.values[(service_name, username)]


class FailingKeyring:
    def get_password(self, service_name: str, username: str) -> str | None:
        raise RuntimeError("backend leaked backend-secret")

    def set_password(
        self, service_name: str, username: str, password: str
    ) -> None:
        raise RuntimeError(f"backend leaked {password}")

    def delete_password(self, service_name: str, username: str) -> None:
        raise RuntimeError("backend leaked backend-secret")


class RecordingStore:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.get_calls = 0
        self.set_calls: list[str] = []
        self.clear_calls = 0

    def get(self) -> str | None:
        self.get_calls += 1
        return self.value

    def set(self, value: str) -> None:
        if not value:
            raise ValueError("credential cannot be empty")
        self.set_calls.append(value)
        self.value = value

    def clear(self) -> bool:
        self.clear_calls += 1
        existed = self.value is not None
        self.value = None
        return existed


def test_store_round_trip_and_clear_uses_fixed_service_and_account() -> None:
    backend = FakeKeyring()
    store = CredentialStore(backend)

    store.set("test-secret")

    assert backend.values == {(SERVICE_NAME, ACCOUNT_NAME): "test-secret"}
    assert store.get() == "test-secret"
    assert store.clear() is True
    assert store.get() is None
    assert store.clear() is False


def test_store_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="credential cannot be empty"):
        CredentialStore(FakeKeyring()).set("")


def test_store_hides_backend_exception_details() -> None:
    with pytest.raises(CredentialStoreError) as captured:
        CredentialStore(FailingKeyring()).get()

    assert str(captured.value) == "system keyring operation failed"
    assert "backend-secret" not in str(captured.value)


def test_environment_key_has_priority_without_reading_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingStore("keyring-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")

    value, source = resolve_api_key(store)

    assert (value, source) == ("environment-secret", "environment")
    assert store.get_calls == 0


def test_resolve_api_key_falls_back_to_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert resolve_api_key(RecordingStore("keyring-secret")) == (
        "keyring-secret",
        "system keyring",
    )
    assert resolve_api_key(RecordingStore()) == (None, "not configured")


def test_credential_status_never_reveals_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = cli.main(
        ["credential", "status"],
        credential_store=RecordingStore("test-secret"),
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "configured (system keyring)" in captured.out
    assert "test-secret" not in captured.out + captured.err


def test_status_reports_environment_without_reading_keyring(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = RecordingStore("keyring-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")

    assert cli.main(["credential", "status"], credential_store=store) == 0

    captured = capsys.readouterr()
    assert "configured (environment)" in captured.out
    assert "environment-secret" not in captured.out + captured.err
    assert store.get_calls == 0


def test_set_uses_hidden_input_and_update_replaces_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingStore()
    answers = iter(["first-secret", "second-secret"])
    monkeypatch.setattr(cli, "_hidden_input", lambda prompt: next(answers))

    assert cli.main(["credential", "set"], credential_store=store) == 0
    assert cli.main(["credential", "update"], credential_store=store) == 0

    assert store.set_calls == ["first-secret", "second-secret"]
    assert store.value == "second-secret"


def test_set_refuses_to_overwrite_and_update_requires_existing_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_hidden_input", lambda prompt: "unused-secret")

    assert (
        cli.main(
            ["credential", "set"],
            credential_store=RecordingStore("existing-secret"),
        )
        == 2
    )
    assert "credential update" in capsys.readouterr().err

    assert (
        cli.main(["credential", "update"], credential_store=RecordingStore()) == 2
    )
    assert "credential set" in capsys.readouterr().err


def test_empty_hidden_input_is_rejected_without_storing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = RecordingStore()
    monkeypatch.setattr(cli, "_hidden_input", lambda prompt: "")

    assert cli.main(["credential", "set"], credential_store=store) == 2

    assert store.set_calls == []
    assert "cannot be empty" in capsys.readouterr().err


def test_clear_is_idempotent_and_never_prints_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = RecordingStore("test-secret")

    assert cli.main(["credential", "clear"], credential_store=store) == 0
    assert cli.main(["credential", "clear"], credential_store=store) == 0

    captured = capsys.readouterr()
    assert store.clear_calls == 2
    assert "test-secret" not in captured.out + captured.err


def test_cli_hides_keyring_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert (
        cli.main(
            ["credential", "status"],
            credential_store=CredentialStore(FailingKeyring()),
        )
        == 2
    )

    captured = capsys.readouterr()
    assert "system keyring operation failed" in captured.err
    assert "backend-secret" not in captured.out + captured.err


def test_serve_falls_back_to_keyring_without_echoing_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FR_DATABASE_PATH", str(tmp_path / "fr.sqlite3"))
    monkeypatch.setenv("FR_LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("FR_LLM_MODEL", "test-model")

    class FakeLLM:
        def __init__(self, base_url: str, model: str, api_key: str) -> None:
            captured.update(base_url=base_url, model=model, api_key=api_key)

    def fake_run(app: object, **kwargs: object) -> None:
        captured["app"] = app

    monkeypatch.setattr(cli, "OpenAICompatibleLLM", FakeLLM)
    monkeypatch.setattr(cli.uvicorn, "run", fake_run)

    assert (
        cli.main(
            ["serve", "--host", "127.0.0.1"],
            credential_store=RecordingStore("keyring-secret"),
        )
        == 0
    )

    output = capsys.readouterr()
    assert captured["api_key"] == "keyring-secret"
    assert "keyring-secret" not in output.out + output.err


def test_noninteractive_serve_without_key_returns_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FR_LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("FR_LLM_MODEL", "test-model")
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: False)

    assert cli.main(["serve"], credential_store=RecordingStore()) == 2

    captured = capsys.readouterr()
    assert "credential set" in captured.err


def test_interactive_first_run_prompts_and_saves_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingStore()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FR_DATABASE_PATH", str(tmp_path / "fr.sqlite3"))
    monkeypatch.setenv("FR_LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("FR_LLM_MODEL", "test-model")
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr(cli, "_hidden_input", lambda prompt: "prompted-secret")
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: None)

    class FakeLLM:
        def __init__(self, base_url: str, model: str, api_key: str) -> None:
            assert api_key == "prompted-secret"

    monkeypatch.setattr(cli, "OpenAICompatibleLLM", FakeLLM)

    assert cli.main(["serve"], credential_store=store) == 0
    assert store.set_calls == ["prompted-secret"]
