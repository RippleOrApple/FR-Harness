import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "demo" / "mock_repair_demo.py"
EXPECTED_LINES = [
    "guardrail approval: PASS",
    "feedback repair: PASS",
    "approval one-time use: PASS",
]


def test_mock_repair_demo_prints_exact_pass_lines() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == EXPECTED_LINES
    assert completed.stderr == ""


def test_demo_source_is_offline_and_temporary() -> None:
    source = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""

    assert "TemporaryDirectory" in source
    assert "MockLLM" in source
    assert "OpenAICompatibleLLM" not in source
    assert "os.environ" not in source
    assert "OPENAI_API_KEY" not in source

