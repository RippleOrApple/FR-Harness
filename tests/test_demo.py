import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "demo" / "mock_repair_demo.py"
EXPECTED_LINES = [
    "危险操作审批：PASS",
    "失败反馈纠错：PASS",
    "一次性文件审批：PASS",
    "任务级 pytest 权限：PASS",
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


def test_packaged_demo_is_offline_and_temporary() -> None:
    source = (ROOT / "src" / "fr_harness" / "demo.py").read_text(encoding="utf-8")

    assert "TemporaryDirectory" in source
    assert "MockLLM" in source
    assert "OpenAICompatibleLLM" not in source
    assert "os.environ" not in source
    assert "OPENAI_API_KEY" not in source

