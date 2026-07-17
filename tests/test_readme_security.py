import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_usage_and_security_in_utf8() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = readme.lower()

    for required in (
        "OPENAI_API_KEY",
        ".env",
        "明文",
        "docker build",
        "MockLLM",
        "工作区",
        "已知限制",
        "python -m pytest -v",
    ):
        assert required.lower() in lowered
    assert "## 安全" in readme
    assert "## Docker" in readme
    assert not re.search(r"\bsk-[A-Za-z0-9_-]{20,}\b", readme)


def test_gitlab_ci_runs_tests_and_builds_image() -> None:
    pipeline = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert re.search(r"(?m)^unit-test:\s*$", pipeline)
    assert 'python -m pip install ".[dev]"' in pipeline
    assert "python -m pytest -v" in pipeline
    assert "docker build" in pipeline

