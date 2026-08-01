import subprocess
import sys
import os
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pytest_is_a_runtime_dependency_for_agent_tasks() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]

    assert any(item.startswith("pytest>=") for item in project["dependencies"])


def test_package_exposes_versioned_console_entrypoint() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "fr_harness.cli", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        env=environment,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == "FR-Harness 1.0.0"


def test_windows_release_definition_contains_verified_artifacts() -> None:
    spec = (ROOT / "fr-harness.spec").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    quick_start = (ROOT / "release" / "快速开始.txt").read_text(encoding="utf-8")

    assert "onefile" not in spec.lower()
    assert "console=True" in spec
    assert "fr-harness" in spec.lower()
    assert "windows-latest" in workflow
    assert "python -m pytest" in workflow
    assert "pyinstaller --clean fr-harness.spec" in workflow
    assert "fr-harness.exe --version" in workflow.lower()
    assert "fr-harness.exe demo" in workflow.lower()
    assert "fr-harness.exe _pytest" in workflow.lower()
    assert "Compress-Archive" in workflow
    assert "Get-FileHash" in workflow
    assert "gh release create" in workflow
    assert "无需安装 Python" in quick_start
    assert "FR-Harness.exe demo" in quick_start
