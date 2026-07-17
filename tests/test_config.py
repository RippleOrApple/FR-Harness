from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from fr_harness import cli
from fr_harness.agent import Agent
from fr_harness.config import (
    AgentSettings,
    ApprovalSettings,
    HarnessConfig,
    load_config,
)
from fr_harness.db import Database
from fr_harness.guardrails import GuardDecision, classify
from fr_harness.llm import MockLLM
from fr_harness.models import Action, ActionKind, TaskStatus
from fr_harness.web import create_app


class RecordingMemory:
    def __init__(self) -> None:
        self.observed_limit: int | None = None

    def relevant(self, task_id: UUID, limit: int = 5) -> list[str]:
        self.observed_limit = limit
        return []

    def add(self, task_id: UUID, category: str, content: str) -> None:
        return None


def allow_all(action: Action, workspace: Path) -> GuardDecision:
    return GuardDecision.ALLOWED


def test_default_config_has_safe_limits_and_approvals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    config = load_config(environ={})

    assert config.agent.max_iterations == 8
    assert config.agent.memory_limit == 5
    assert config.approvals.existing_file_write is True
    assert config.approvals.run_pytest is True


def test_toml_and_environment_override_config(tmp_path: Path) -> None:
    path = tmp_path / "fr-harness.toml"
    path.write_text(
        "[agent]\n"
        "max_iterations = 3\n"
        "memory_limit = 2\n"
        "[approvals]\n"
        "existing_file_write = true\n"
        "run_pytest = false\n",
        encoding="utf-8",
    )

    config = load_config(
        path,
        {
            "FR_MAX_ITERATIONS": "4",
            "FR_APPROVE_EXISTING_WRITE": "no",
        },
    )

    assert config.agent.max_iterations == 4
    assert config.agent.memory_limit == 2
    assert config.approvals.existing_file_write is False
    assert config.approvals.run_pytest is False


def test_environment_config_path_is_loaded(tmp_path: Path) -> None:
    path = tmp_path / "custom.toml"
    path.write_text("[agent]\nmemory_limit = 7\n", encoding="utf-8")

    config = load_config(environ={"FR_CONFIG_PATH": str(path)})

    assert config.agent.memory_limit == 7


@pytest.mark.parametrize("value", ["sometimes", "2", ""])
def test_invalid_boolean_environment_value_fails(value: str) -> None:
    with pytest.raises(ValueError, match="invalid boolean configuration"):
        load_config(environ={"FR_APPROVE_PYTEST": value})


def test_config_rejects_nonpositive_limits_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AgentSettings(max_iterations=0)
    with pytest.raises(ValidationError):
        AgentSettings(memory_limit=-1)
    with pytest.raises(ValidationError):
        HarnessConfig.model_validate({"unknown": True})


def test_policy_can_relax_approvals_but_never_workspace_escape(
    tmp_path: Path,
) -> None:
    (tmp_path / "existing.py").write_text("old", encoding="utf-8")
    policy = ApprovalSettings(existing_file_write=False, run_pytest=False)

    assert (
        classify(
            Action(kind=ActionKind.WRITE_FILE, path="existing.py", content="new"),
            tmp_path,
            policy,
        )
        is GuardDecision.ALLOWED
    )
    assert (
        classify(Action(kind=ActionKind.RUN_PYTEST), tmp_path, policy)
        is GuardDecision.ALLOWED
    )
    assert (
        classify(
            Action(kind=ActionKind.READ_FILE, path="../secret.txt"),
            tmp_path,
            policy,
        )
        is GuardDecision.BLOCKED
    )


def test_agent_uses_configured_memory_and_iteration_limits(tmp_path: Path) -> None:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()
    (tmp_path / "a.py").write_text("a = 1", encoding="utf-8")
    task = database.create_task("inspect", tmp_path)
    memory = RecordingMemory()
    config = HarnessConfig(
        agent={"max_iterations": 1, "memory_limit": 1},
    )
    llm = MockLLM(
        [
            Action(kind=ActionKind.READ_FILE, path="a.py"),
            Action(kind=ActionKind.READ_FILE, path="a.py"),
        ]
    )

    result = Agent(
        database,
        llm,
        config=config,
        memory=memory,
        classifier=allow_all,
    ).run_until_stopped(task.id)

    assert result.status is TaskStatus.FAILED
    assert result.iteration == 1
    assert memory.observed_limit == 1


def test_create_app_injects_configured_agent_limits(tmp_path: Path) -> None:
    config = HarnessConfig(agent={"max_iterations": 3, "memory_limit": 2})

    app = create_app(tmp_path / "fr.sqlite3", MockLLM([]), config=config)

    assert app.state.agent.max_iterations == 3
    assert app.state.agent.memory_limit == 2


def test_serve_loads_declarative_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FR_DATABASE_PATH", str(tmp_path / "fr.sqlite3"))
    monkeypatch.setenv("FR_LLM_BASE_URL", "https://llm.invalid/v1")
    monkeypatch.setenv("FR_LLM_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("FR_MAX_ITERATIONS", "3")

    class FakeLLM:
        def __init__(self, base_url: str, model: str, api_key: str) -> None:
            return None

    def fake_run(app: object, **kwargs: object) -> None:
        captured["app"] = app

    monkeypatch.setattr(cli, "OpenAICompatibleLLM", FakeLLM)
    monkeypatch.setattr(cli.uvicorn, "run", fake_run)

    assert cli.main(["serve"]) == 0

    app = captured["app"]
    assert app.state.agent.max_iterations == 3
