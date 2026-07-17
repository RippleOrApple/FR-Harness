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


def test_documented_modules_and_commands_match_repository() -> None:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "`actions`" not in spec
    assert "`audit`" not in spec
    assert "credentials.py" in readme
    assert "config.py" in readme
    assert "credentials.py" in plan
    assert "config.py" in plan
    for command in (
        "credential set",
        "credential status",
        "credential update",
        "credential clear",
    ):
        assert command in readme


def test_readme_explains_credential_and_rule_precedence() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required in (
        "环境变量优先",
        "system keyring",
        "fr-harness.toml",
        "Windows Credential Manager",
        "Docker",
        "平台 Secret",
    ):
        assert required.lower() in readme.lower()


EXPECTED_TASK_HASHES = {
    1: "915b27b",
    2: "82b1436",
    3: "1b41219",
    4: "975f767",
    5: "2ca4a0c",
    6: "7ce1a8c",
    7: "c770f4a",
    8: "8c154d0",
    9: "4e6dc52",
    10: "5e38784",
    11: "c1abe9b",
    12: "2d45d44",
}


def test_plan_records_real_hash_for_every_completed_task() -> None:
    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8")

    for task, commit_hash in EXPECTED_TASK_HASHES.items():
        task_section = re.search(
            rf"(?ms)^## Task {task}：.*?(?=^## Task \d+：|\Z)",
            plan,
        )
        assert task_section is not None
        assert commit_hash in task_section.group(0)


def test_agent_log_names_context_human_judgment_and_honest_deviation() -> None:
    log = (ROOT / "AGENT_LOG.md").read_text(encoding="utf-8")

    for required in (
        "关键 prompt / context",
        "人工判断",
        "偏差",
        "OpenCode",
        "后补评审",
        "不能倒签",
    ):
        assert required in log
