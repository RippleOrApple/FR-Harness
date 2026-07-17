import os
import tomllib
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AgentSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_iterations: int = Field(default=8, ge=1, le=100)
    memory_limit: int = Field(default=5, ge=1, le=100)


class ApprovalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing_file_write: bool = True
    run_pytest: bool = True


class HarnessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: AgentSettings = Field(default_factory=AgentSettings)
    approvals: ApprovalSettings = Field(default_factory=ApprovalSettings)


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("invalid boolean configuration")


def load_config(
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> HarnessConfig:
    values = os.environ if environ is None else environ
    selected = path
    if selected is None and values.get("FR_CONFIG_PATH"):
        selected = Path(values["FR_CONFIG_PATH"]).expanduser()
    if selected is None and Path("fr-harness.toml").is_file():
        selected = Path("fr-harness.toml")

    data: dict[str, object] = {}
    if selected is not None:
        with selected.open("rb") as stream:
            data = tomllib.load(stream)

    agent = dict(data.get("agent", {}))
    approvals = dict(data.get("approvals", {}))
    if "FR_MAX_ITERATIONS" in values:
        agent["max_iterations"] = int(values["FR_MAX_ITERATIONS"])
    if "FR_MEMORY_LIMIT" in values:
        agent["memory_limit"] = int(values["FR_MEMORY_LIMIT"])
    if "FR_APPROVE_EXISTING_WRITE" in values:
        approvals["existing_file_write"] = parse_boolean(
            values["FR_APPROVE_EXISTING_WRITE"]
        )
    if "FR_APPROVE_PYTEST" in values:
        approvals["run_pytest"] = parse_boolean(values["FR_APPROVE_PYTEST"])
    return HarnessConfig.model_validate(
        {"agent": agent, "approvals": approvals}
    )
