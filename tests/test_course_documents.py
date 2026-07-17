import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SPEC_HEADINGS = [
    "问题陈述",
    "用户故事",
    "功能规约",
    "非功能性需求",
    "系统架构",
    "数据模型",
    "凭据与分发设计",
    "技术选型与理由",
    "验收标准",
    "风险与未决问题",
    "领域与机制设计",
]


def test_spec_contains_required_course_sections_and_five_invest_stories() -> None:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")

    for heading in SPEC_HEADINGS:
        assert heading in spec
    assert len(re.findall(r"(?m)^### US-\d+：", spec)) >= 5
    for required in (
        "性能",
        "安全",
        "可用性",
        "可观测性",
        "威胁模型",
        "keyring",
    ):
        assert required.lower() in spec.lower()


def test_spec_defines_harness_mechanisms_and_module_contracts() -> None:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")

    for mechanism in ("动作 / 工具", "客观反馈信号", "危险动作", "记忆"):
        assert mechanism in spec
    assert "主要贡献" in spec
    assert "治理" in spec
    for contract_field in ("输入", "行为", "输出", "边界条件", "错误处理"):
        assert contract_field in spec


def test_spec_explains_stack_distribution_and_acceptance_evidence() -> None:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")

    for choice in (
        "Python 3.12",
        "FastAPI",
        "SQLite",
        "OpenAI 兼容",
        "Docker",
        "GHCR",
    ):
        assert choice.lower() in spec.lower()
    for evidence in (
        "tests/test_agent.py",
        "tests/test_guardrails.py",
        "tests/test_credentials.py",
        "demo/mock_repair_demo.py",
    ):
        assert evidence in spec


def test_spec_process_records_three_iterations_and_honest_evidence() -> None:
    process = (ROOT / "SPEC_PROCESS.md").read_text(encoding="utf-8")

    assert len(re.findall(r"(?m)^## 迭代 \d+：", process)) >= 3
    for required in (
        "AI 建议",
        "用户判断",
        "修订",
        "证据",
        "回顾性整理",
        "不伪造",
        "冷启动验证",
        "冷启动复验",
    ):
        assert required in process


def test_spec_process_reflects_on_brainstorming_strengths_and_limits() -> None:
    process = (ROOT / "SPEC_PROCESS.md").read_text(encoding="utf-8")

    assert "brainstorming 做得好的地方" in process
    assert "brainstorming 让人不满的地方" in process
    assert "人的最终判断" in process
