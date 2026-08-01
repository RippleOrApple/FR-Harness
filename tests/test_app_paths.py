from pathlib import Path

from fr_harness.app_paths import RuntimePaths


def test_runtime_paths_use_explicit_data_directory(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "harness-data"
    monkeypatch.setenv("FR_DATA_DIR", str(data_dir))

    paths = RuntimePaths.from_environment(frozen=False)
    paths.ensure()

    assert paths.root == data_dir.resolve()
    assert paths.env_file == data_dir.resolve() / ".env"
    assert paths.config_file == data_dir.resolve() / "fr-harness.toml"
    assert paths.database_file == data_dir.resolve() / "fr_harness.sqlite3"
    assert paths.log_dir.is_dir()


def test_frozen_runtime_paths_use_windows_local_app_data(
    monkeypatch, tmp_path: Path
) -> None:
    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.delenv("FR_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    paths = RuntimePaths.from_environment(frozen=True)

    assert paths.root == (local_app_data / "FR-Harness").resolve()


def test_source_runtime_paths_default_to_current_directory(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("FR_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    paths = RuntimePaths.from_environment(frozen=False)

    assert paths.root == tmp_path.resolve()
