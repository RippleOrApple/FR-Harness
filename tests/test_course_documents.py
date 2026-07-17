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
