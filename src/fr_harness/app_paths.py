import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    env_file: Path
    config_file: Path
    database_file: Path
    log_dir: Path

    @classmethod
    def from_environment(cls, *, frozen: bool | None = None) -> "RuntimePaths":
        explicit = os.environ.get("FR_DATA_DIR")
        is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        if explicit:
            root = Path(explicit).expanduser().resolve()
        elif is_frozen:
            local_app_data = os.environ.get("LOCALAPPDATA")
            base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
            root = (base / "FR-Harness").resolve()
        else:
            root = Path.cwd().resolve()
        return cls(
            root=root,
            env_file=root / ".env",
            config_file=root / "fr-harness.toml",
            database_file=root / "fr_harness.sqlite3",
            log_dir=root / "logs",
        )

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
