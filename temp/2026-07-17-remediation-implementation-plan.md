# FR-Harness 前十项补救 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 FR-Harness 的安全凭据、声明式配置、规格与过程证据、GitHub Actions、PR/CI 和公共容器镜像交付链。

**Architecture:** 凭据通过可注入的 `CredentialStore` 访问操作系统 keyring，运行时保留环境变量优先级和容器回退；Agent 行为通过 TOML 加载的 Pydantic 配置约束。课程文档使用自动化结构测试防止再次漂移，GitHub Actions 负责离线测试、Docker 冷启动与主分支 GHCR 发布。

**Tech Stack:** Python 3.12、Pydantic v2、keyring、FastAPI、SQLite、pytest、Docker、GitHub Actions、GHCR、OpenCode CLI、GitHub CLI。

## Global Constraints

- 仅支持 Python 工作区；修复的客观反馈信号是 `pytest`。
- 不得使用 LangChain、AutoGen、CrewAI、LlamaIndex Agent 或任何现成 Agent 主循环。
- 所有核心机制必须能在无网络、无真实模型时用 MockLLM 测试。
- 所有文件路径必须解析并限制在任务绑定的工作区根目录内。
- API Key 不得写入源码、SQLite、审计记录、日志、响应、终端 history 或明文配置文件。
- 环境变量优先于系统 keyring；Docker 和 CI 通过环境变量注入凭据。
- 默认最多运行 8 轮、记忆最多注入 5 条；连续两次相同动作则任务失败。
- 覆盖已有文件与运行 pytest 默认要求一次性人工批准。
- 历史上没有发生的 subagent、评审、PR、CI 或 brainstorming 不得倒签或伪造。
- 本轮新建的 Markdown 文件必须位于 `temp/`；现有根目录交付文档可原位修订。
- 用户现有且未跟踪的 `A任务完成指南.md` 不得纳入提交。

## File Structure

| 路径 | 职责 |
| --- | --- |
| `src/fr_harness/credentials.py` | keyring 后端协议、凭据读写和安全错误归一化 |
| `src/fr_harness/config.py` | TOML/环境变量声明式配置模型与加载 |
| `src/fr_harness/cli.py` | 凭据生命周期命令、首次运行引导、服务配置 |
| `src/fr_harness/agent.py` | 消费迭代和记忆配置 |
| `src/fr_harness/guardrails.py` | 消费声明式审批策略 |
| `src/fr_harness/web.py` | 将配置注入 Agent |
| `fr-harness.toml` | 不含秘密的安全默认规则 |
| `tests/test_credentials.py` | keyring 和 CLI 凭据生命周期离线测试 |
| `tests/test_config.py` | 配置默认值、覆盖、非法输入与运行时注入测试 |
| `tests/test_course_documents.py` | SPEC/过程/PLAN/结构追踪测试 |
| `tests/test_github_actions.py` | GitHub Actions 与 GHCR 发布结构测试 |
| `.github/workflows/ci.yml` | push/PR 测试、Docker 验证和主分支镜像发布 |
| `SPEC.md` | 完整十项规格、五个用户故事、NFR、威胁模型、A 类机制 |
| `SPEC_PROCESS.md` | 三轮可验证迭代、冷启动差距和当前补救过程 |
| `PLAN.md` | 已完成任务、依赖、验证与真实 commit hash |
| `AGENT_LOG.md` | prompt、技能、评审、人工判断和 commit 证据 |
| `README.md` | keyring、TOML、GitHub CI、GHCR 获取与运行说明 |
| `temp/remediation-task-*/` | 每个补救任务的 GOAL、计划、发现和进度 |
| `temp/reviews/` | OpenCode 规格与代码质量评审记录 |

---

### Task 1: 安全凭据存储与生命周期

**Files:**
- Create: `temp/remediation-task-01/GOAL.md`
- Create: `src/fr_harness/credentials.py`
- Create: `tests/test_credentials.py`
- Modify: `src/fr_harness/cli.py`
- Modify: `pyproject.toml`
- Modify: `.env.example`

**Interfaces:**
- Consumes: `OPENAI_API_KEY` 环境变量和 `keyring` 底层 API。
- Produces: `CredentialStore.get() -> str | None`、`set(value: str) -> None`、`clear() -> bool`；CLI `credential set/status/update/clear`；`resolve_api_key(store, environ) -> tuple[str | None, str]`。

- [ ] **Step 1: 创建 GOAL 并启动 planning-with-files**

`temp/remediation-task-01/GOAL.md` 必须写明：实现操作系统 keyring 生命周期；环境变量优先；不得打印秘密；测试必须使用 fake backend 且不访问真实 keyring。随后在同目录创建 `task_plan.md`、`findings.md`、`progress.md`。

- [ ] **Step 2: 先写失败测试**

在 `tests/test_credentials.py` 中定义只保存内存的 fake，不访问真实 keyring：

```python
from pathlib import Path

import pytest

from fr_harness import cli
from fr_harness.credentials import CredentialStore, resolve_api_key


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def set_password(
        self, service_name: str, username: str, password: str
    ) -> None:
        self.values[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        del self.values[(service_name, username)]


class RecordingStore:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.get_calls = 0

    def get(self) -> str | None:
        self.get_calls += 1
        return self.value

    def set(self, value: str) -> None:
        self.value = value

    def clear(self) -> bool:
        existed = self.value is not None
        self.value = None
        return existed


def test_store_round_trip_and_clear_uses_fixed_service_and_account() -> None:
    backend = FakeKeyring()
    store = CredentialStore(backend)
    store.set("test-secret")
    assert store.get() == "test-secret"
    assert store.clear() is True
    assert store.get() is None

def test_environment_key_has_priority_without_reading_keyring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingStore("keyring-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")
    value, source = resolve_api_key(store)
    assert (value, source) == ("environment-secret", "environment")
    assert store.get_calls == 0

def test_credential_status_never_reveals_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        ["credential", "status"],
        credential_store=RecordingStore("test-secret"),
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "configured" in captured.out.lower()
    assert "test-secret" not in captured.out + captured.err

def test_set_uses_hidden_input_and_update_replaces_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingStore()
    monkeypatch.setattr(cli, "_hidden_input", lambda prompt: "first-secret")
    assert cli.main(["credential", "set"], credential_store=store) == 0
    monkeypatch.setattr(cli, "_hidden_input", lambda prompt: "second-secret")
    assert cli.main(["credential", "update"], credential_store=store) == 0
    assert store.get() == "second-secret"
```

另加测试：空输入失败、`set` 不覆盖已有值、`update` 要求已有值、`clear` 幂等、keyring 异常只输出通用错误、`serve` 在无环境 key 时读取 store、非交互式缺 key 时返回 2 并提示运行 `credential set`。

- [ ] **Step 3: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_credentials.py -v`

Expected: FAIL，原因是 `fr_harness.credentials` 或新增 CLI 接口尚不存在。

- [ ] **Step 4: 实现最小凭据模块**

`src/fr_harness/credentials.py` 使用以下固定边界：

```python
import os
from collections.abc import Mapping
from typing import Protocol

import keyring


SERVICE_NAME = "fr-harness"
ACCOUNT_NAME = "openai-api-key"

class KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None:
        raise NotImplementedError

    def set_password(
        self, service_name: str, username: str, password: str
    ) -> None:
        raise NotImplementedError

    def delete_password(self, service_name: str, username: str) -> None:
        raise NotImplementedError

class CredentialStoreError(RuntimeError):
    pass

class CredentialStore:
    def __init__(self, backend: KeyringBackend | None = None) -> None:
        self._backend = backend or keyring

    def get(self) -> str | None:
        try:
            return self._backend.get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as error:
            raise CredentialStoreError("system keyring operation failed") from error

    def set(self, value: str) -> None:
        if not value:
            raise ValueError("credential cannot be empty")
        try:
            self._backend.set_password(SERVICE_NAME, ACCOUNT_NAME, value)
        except Exception as error:
            raise CredentialStoreError("system keyring operation failed") from error

    def clear(self) -> bool:
        if self.get() is None:
            return False
        try:
            self._backend.delete_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as error:
            raise CredentialStoreError("system keyring operation failed") from error
        return True

def resolve_api_key(
    store: CredentialStore,
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, str]:
    values = os.environ if environ is None else environ
    environment_value = values.get("OPENAI_API_KEY")
    if environment_value:
        return environment_value, "environment"
    keyring_value = store.get()
    if keyring_value:
        return keyring_value, "system keyring"
    return None, "not configured"
```

`CredentialStore` 将底层异常转换为不包含原始异常文本和凭据值的 `CredentialStoreError`；空值在写入前抛出 `ValueError("credential cannot be empty")`；删除不存在的凭据返回 `False`。

`cli.main()` 增加可选 `credential_store` 注入点。命令语义固定为：

- `set`：已有 keyring 值时返回 2，提示使用 `update`；
- `update`：不存在时返回 2，提示使用 `set`；
- `clear`：存在或不存在都返回 0；
- `status`：环境变量存在时显示 `configured (environment)`，否则显示 `configured (system keyring)` 或 `not configured`；
- 所有录入均使用 `getpass.getpass()` 封装的 `_hidden_input()`。

`_serve()` 只缺 API key 且处于交互式终端时隐藏录入并保存到 keyring；非交互式终端提示 `fr-harness credential set`。`FR_LLM_BASE_URL` 或 `FR_LLM_MODEL` 缺失时仍返回通用配置错误。

- [ ] **Step 5: 增加依赖并运行绿灯**

在 `pyproject.toml` 的 dependencies 增加 `"keyring>=25"`，并执行：

Run: `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_credentials.py tests/test_cli.py -v`

Expected: PASS，输出中不存在测试密钥。

- [ ] **Step 6: 提交**

```powershell
git add pyproject.toml .env.example src/fr_harness/credentials.py src/fr_harness/cli.py tests/test_credentials.py temp/remediation-task-01
git commit -m "feat: add secure credential lifecycle"
```

---

### Task 2: 补全 SPEC 十项结构、用户故事、NFR 与威胁模型

**Files:**
- Create: `temp/remediation-task-02/GOAL.md`
- Create: `tests/test_course_documents.py`
- Modify: `SPEC.md`

**Interfaces:**
- Consumes: `AI4SE_Final_Project_A_Coding_Agent_Harness.md` 与 `通用要求.md`。
- Produces: 可由自动化结构测试检查的完整 `SPEC.md`。

- [ ] **Step 1: 创建 GOAL**

GOAL 明确要求保留现有有效机制约定，并重组为通用要求 §4.2 的十项结构，加独立的“领域与机制设计”章节。

- [ ] **Step 2: 写文档结构红灯测试**

`tests/test_course_documents.py` 检查：

```python
SPEC_HEADINGS = [
    "问题陈述", "用户故事", "功能规约", "非功能性需求", "系统架构",
    "数据模型", "凭据与分发设计", "技术选型与理由", "验收标准",
    "风险与未决问题", "领域与机制设计",
]

def test_spec_contains_required_course_sections_and_five_invest_stories() -> None:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    for heading in SPEC_HEADINGS:
        assert heading in spec
    assert len(re.findall(r"(?m)^### US-\\d+：", spec)) >= 5
    for required in ("性能", "安全", "可用性", "可观测性", "威胁", "keyring"):
        assert required.lower() in spec.lower()
```

再检查四类机制“动作 / 工具、客观反馈信号、危险动作、记忆”、主要贡献“治理”、每个模块的输入/行为/输出/边界/错误、验收—测试映射、Python/FastAPI/SQLite/OpenAI 兼容 API/Docker/GHCR 选型理由。

- [ ] **Step 3: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py::test_spec_contains_required_course_sections_and_five_invest_stories -v`

Expected: FAIL，至少缺少“用户故事”“非功能性需求”“凭据与分发设计”等结构。

- [ ] **Step 4: 重写 SPEC**

`SPEC.md` 使用十个编号章节和第十一章“领域与机制设计”。五个用户故事分别覆盖：

1. 开发者创建并运行受限修复任务；
2. 审批者在副作用前批准或拒绝危险动作；
3. 开发者通过失败测试获得自动修复闭环；
4. 操作者安全录入、查看状态、更新和清除 API key；
5. 新用户从公开镜像启动并使用自己的 key。

威胁模型至少列出：源码/Git 泄漏、shell history、`.env` 明文、进程环境、日志/审计、WebUI、容器层/构建上下文、工作区逃逸、keyring 不可用；逐项说明资产、攻击面、控制和剩余风险。

- [ ] **Step 5: 验证并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py -v`

Expected: SPEC 相关断言 PASS。

```powershell
git add SPEC.md tests/test_course_documents.py temp/remediation-task-02
git commit -m "docs: complete course specification"
```

---

### Task 3: 补全 SPEC_PROCESS 的三轮真实迭代

**Files:**
- Create: `temp/remediation-task-03/GOAL.md`
- Modify: `SPEC_PROCESS.md`
- Modify: `tests/test_course_documents.py`

**Interfaces:**
- Consumes: 可验证会话决策、Git 历史和现有冷启动记录。
- Produces: 至少三轮、明确“AI 建议/用户判断/修订/证据”的过程文档。

- [ ] **Step 1: 创建 GOAL**

GOAL 明确禁止补写无法验证的逐字对话；允许用“回顾性整理”标注从会话与 Git 恢复的事实。

- [ ] **Step 2: 扩展红灯测试**

```python
def test_spec_process_records_three_iterations_and_honest_evidence() -> None:
    process = (ROOT / "SPEC_PROCESS.md").read_text(encoding="utf-8")
    assert len(re.findall(r"(?m)^## 迭代 \\d+：", process)) >= 3
    for required in ("AI 建议", "用户判断", "修订", "证据", "回顾性整理", "不伪造"):
        assert required in process
    assert "冷启动验证" in process
    assert "冷启动复验" in process
```

- [ ] **Step 3: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py::test_spec_process_records_three_iterations_and_honest_evidence -v`

Expected: FAIL，因为当前只有冷启动记录，没有三轮 brainstorming 结构。

- [ ] **Step 4: 写入三轮以上可验证迭代**

记录以下事实：

- 迭代 1（回顾性整理）：确定 A 路线、轻量单进程架构与治理重点；精确旧对话缺失，不伪造逐字稿。
- 迭代 2（回顾性整理）：用户纠正项目名为 `FR-Harness`、要求根目录 `SPEC.md`/`PLAN.md`、取消 `docs/`、采用 `src/fr_harness/`。
- 迭代 3（有现存证据）：用户指出阶段 2 冷启动验证未写入 PLAN，允许使用 OpenCode；记录首次阻塞、修订 diff 和复验。
- 迭代 4（本轮完整证据）：比较最小补丁/评分项驱动/整体重构，用户批准评分项驱动以及 `keyring + 环境变量回退`。

补充对 brainstorming 优点、不满和人的最终责任的反思；保留原冷启动技术记录。

- [ ] **Step 5: 验证并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py -v`

Expected: PASS。

```powershell
git add SPEC_PROCESS.md tests/test_course_documents.py temp/remediation-task-03
git commit -m "docs: record specification iterations"
```

---

### Task 4: 声明式 Agent 配置与空模块清理

**Files:**
- Create: `temp/remediation-task-04/GOAL.md`
- Create: `tests/test_config.py`
- Create: `fr-harness.toml`
- Modify: `src/fr_harness/config.py`
- Modify: `src/fr_harness/guardrails.py`
- Modify: `src/fr_harness/agent.py`
- Modify: `src/fr_harness/web.py`
- Modify: `src/fr_harness/cli.py`
- Modify: `Dockerfile`
- Delete: `src/fr_harness/actions.py`

**Interfaces:**
- Consumes: TOML `[agent]`、`[approvals]` 和 `FR_CONFIG_PATH`。
- Produces: `HarnessConfig`、`AgentSettings`、`ApprovalSettings`、`load_config()`；可配置 Agent 迭代/记忆和审批策略。

- [ ] **Step 1: 创建 GOAL**

GOAL 要求安全默认、非法配置快速失败、现有 Agent 调用兼容、删除无职责的 `actions.py` 并同步文档。

- [ ] **Step 2: 写失败测试**

```python
def test_default_config_has_safe_limits_and_approvals() -> None:
    config = load_config(path=None, environ={})
    assert config.agent.max_iterations == 8
    assert config.agent.memory_limit == 5
    assert config.approvals.existing_file_write is True
    assert config.approvals.run_pytest is True

def test_toml_and_environment_override_config(tmp_path: Path) -> None:
    path = tmp_path / "fr-harness.toml"
    path.write_text(
        "[agent]\\nmax_iterations=3\\nmemory_limit=2\\n"
        "[approvals]\\nexisting_file_write=true\\nrun_pytest=false\\n",
        encoding="utf-8",
    )
    config = load_config(path, {"FR_MAX_ITERATIONS": "4"})
    assert config.agent.max_iterations == 4
    assert config.agent.memory_limit == 2
    assert config.approvals.run_pytest is False

class RecordingMemory:
    def __init__(self) -> None:
        self.observed_limit: int | None = None

    def relevant(self, task_id: UUID, limit: int = 5) -> list[str]:
        self.observed_limit = limit
        return []

    def add(self, task_id: UUID, category: str, content: str) -> None:
        return None

def test_agent_uses_configured_memory_limit(tmp_path: Path) -> None:
    database = Database(tmp_path / "fr.sqlite3")
    database.initialize()
    task = database.create_task("inspect", tmp_path)
    memory = RecordingMemory()
    config = HarnessConfig(agent={"max_iterations": 3, "memory_limit": 1})
    llm = MockLLM([Action(kind=ActionKind.COMPLETE, reason="done")])
    Agent(database, llm, config=config, memory=memory).run_once(task.id)
    assert memory.observed_limit == 1
```

该测试文件顶部显式导入 `UUID`、`Path`、`Agent`、`HarnessConfig`、`load_config`、`Database`、`MockLLM`、`Action`、`ActionKind`。另测：0/负数限制被 Pydantic 拒绝、非法布尔环境变量报错、`classify()` 在 `run_pytest=False` 时允许测试但仍阻断路径逃逸、`create_app(database_path, llm, config=config)` 注入同一规则。

- [ ] **Step 3: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v`

Expected: FAIL，因为配置模型和注入点尚不存在。

- [ ] **Step 4: 实现配置模型和加载器**

核心模型固定为：

```python
class AgentSettings(BaseModel):
    max_iterations: int = Field(default=8, ge=1, le=100)
    memory_limit: int = Field(default=5, ge=1, le=100)

class ApprovalSettings(BaseModel):
    existing_file_write: bool = True
    run_pytest: bool = True

class HarnessConfig(BaseModel):
    agent: AgentSettings = Field(default_factory=AgentSettings)
    approvals: ApprovalSettings = Field(default_factory=ApprovalSettings)

def load_config(
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> HarnessConfig:
    values = os.environ if environ is None else environ
    selected = path
    if selected is None and values.get("FR_CONFIG_PATH"):
        selected = Path(values["FR_CONFIG_PATH"])
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
```

该模块导入 `os`、`tomllib`、`Mapping`、`Path` 和 Pydantic 的 `BaseModel`、`Field`。`parse_boolean(value: str) -> bool` 将 `true/1/yes/on` 映射为 True、`false/0/no/off` 映射为 False，其他值抛出 `ValueError("invalid boolean configuration")`。`load_config` 读取显式 path；否则读取 `FR_CONFIG_PATH`；两者都没有时只在当前目录存在 `fr-harness.toml` 才读取。

`classify(action, root, policy=None)` 保持旧调用兼容；路径逃逸永远 blocked，不受配置关闭审批影响。`Agent` 的显式 `max_iterations` 和 `classifier` 仍可覆盖配置，默认使用配置。`memory.relevant()` 使用 `memory_limit`。

- [ ] **Step 5: 写安全默认 TOML 并清理结构**

`fr-harness.toml`：

```toml
[agent]
max_iterations = 8
memory_limit = 5

[approvals]
existing_file_write = true
run_pytest = true
```

删除空 `actions.py`；动作模型继续唯一位于 `models.py`。Dockerfile 复制 `fr-harness.toml`。

- [ ] **Step 6: 验证并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_agent.py tests/test_guardrails.py tests/test_web.py tests/test_cli.py -v`

Expected: PASS。

```powershell
git add fr-harness.toml Dockerfile src/fr_harness tests/test_config.py temp/remediation-task-04
git commit -m "feat: add declarative agent configuration"
```

---

### Task 5: 修正文档与实现漂移

**Files:**
- Create: `temp/remediation-task-05/GOAL.md`
- Modify: `README.md`
- Modify: `SPEC.md`
- Modify: `PLAN.md`
- Modify: `tests/test_course_documents.py`

**Interfaces:**
- Consumes: 当前 `src/fr_harness/`、CLI help、配置文件与容器行为。
- Produces: 与代码一致的模块图、命令、配置和分发说明。

- [ ] **Step 1: 创建 GOAL 并写红灯测试**

测试断言：

```python
def test_documented_modules_and_commands_match_repository() -> None:
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "`actions`" not in spec
    assert "`audit`" not in spec
    assert "credentials.py" in readme
    assert "config.py" in readme
    for command in ("credential set", "credential status", "credential update", "credential clear"):
        assert command in readme
```

另断言 README 描述环境变量优先、keyring 回退、Docker 不依赖桌面 keyring、`fr-harness.toml` 和 GitHub Actions/GHCR。

- [ ] **Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py::test_documented_modules_and_commands_match_repository -v`

Expected: FAIL，当前 SPEC 仍列 `actions`/`audit`，README 没有凭据命令和配置模块。

- [ ] **Step 3: 同步正式文档**

明确：

- Action 类型位于 `models.py`；
- 审计事件由 `db.py` 持久化；
- `credentials.py` 只负责系统密钥库；
- `config.py` 只负责非秘密规则；
- CLI 精确列出所有命令；
- `.env` 是兼容来源而非安全存储；
- Docker 通过环境变量/平台 Secret 注入；
- WebUI 仍无身份认证，不能暴露在不可信网络。

- [ ] **Step 4: 验证并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py tests/test_readme_security.py -v`

Expected: PASS。

```powershell
git add README.md SPEC.md PLAN.md tests/test_course_documents.py temp/remediation-task-05
git commit -m "docs: align specification with implementation"
```

---

### Task 6: 补齐真实 commit hash 与 Agent 过程证据

**Files:**
- Create: `temp/remediation-task-06/GOAL.md`
- Modify: `PLAN.md`
- Modify: `AGENT_LOG.md`
- Modify: `tests/test_course_documents.py`

**Interfaces:**
- Consumes: `git log` 和本轮实际执行记录。
- Produces: Task 1–12 可定位 hash、历史偏差声明和本轮 prompt/review/人工判断证据。

- [ ] **Step 1: 创建 GOAL 并写失败测试**

```python
EXPECTED_TASK_HASHES = {
    1: "2adfbea", 2: "c218571", 3: "b380d11", 4: "2f7a2dc",
    5: "c0b197c", 6: "0a4b70f", 7: "cb4d677", 8: "1b50c28",
    9: "6c0e19a", 10: "12caf2d", 11: "9c1ef29", 12: "f04e3c5",
}

def test_plan_records_real_hash_for_every_completed_task() -> None:
    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8")
    for task, commit_hash in EXPECTED_TASK_HASHES.items():
        assert re.search(rf"Task {task}.*?{commit_hash}", plan, re.S)
```

另检查 AGENT_LOG 含“关键 prompt / context”“人工判断”“偏差”“OpenCode”，且明确早期 Task 没有逐 task subagent/two-stage review，不能把后补评审写成历史评审。

- [ ] **Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py::test_plan_records_real_hash_for_every_completed_task -v`

Expected: FAIL，Task 4–12 尚无 hash。

- [ ] **Step 3: 写入真实证据**

PLAN 使用以下已验证 hash：

```text
Task 1  2adfbea    Task 2  c218571    Task 3  b380d11
Task 4  2f7a2dc    Task 5  c0b197c    Task 6  0a4b70f
Task 7  cb4d677    Task 8  1b50c28    Task 9  6c0e19a
Task 10 12caf2d    Task 11 9c1ef29    Task 12 f04e3c5
```

AGENT_LOG 增加本轮时间线：用户要求十项补救、`keyring` 选择、三方案比较、设计批准、writing-plans/GOAL/TDD、每个新提交的实际 hash。使用 `git rev-parse --short HEAD` 获取新提交 hash，不预填不存在的值。

- [ ] **Step 4: 验证并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_course_documents.py -v`

Expected: PASS。

```powershell
git add PLAN.md AGENT_LOG.md tests/test_course_documents.py temp/remediation-task-06
git commit -m "docs: complete implementation evidence"
```

---

### Task 7: GitHub Actions 测试、Docker 验证与 GHCR 发布

**Files:**
- Create: `temp/remediation-task-07/GOAL.md`
- Create: `.github/workflows/ci.yml`
- Create: `tests/test_github_actions.py`
- Modify: `Dockerfile`
- Modify: `README.md`

**Interfaces:**
- Consumes: GitHub `GITHUB_TOKEN`、公开仓库、Dockerfile。
- Produces: push/PR CI 和 main 分支 GHCR tags `latest`、`sha-<commit>`。

- [ ] **Step 1: 创建 GOAL 并写失败测试**

```python
def test_github_actions_runs_tests_builds_container_and_publishes_ghcr() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for required in (
        "pull_request:", "push:", "python -m pytest -v",
        "docker build", "curl --fail", "packages: write",
        "ghcr.io/${{ github.repository_owner }}/fr-harness",
        "docker/login-action", "docker/build-push-action",
    ):
        assert required in workflow
```

另检查镜像发布 job 仅在 `refs/heads/main` 执行，依赖测试与 Docker 验证，Dockerfile 包含 `org.opencontainers.image.source`。

- [ ] **Step 2: 运行红灯**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_github_actions.py -v`

Expected: FAIL，因为 `.github/workflows/ci.yml` 不存在。

- [ ] **Step 3: 实现工作流**

工作流必须具有：

```yaml
name: CI
on:
  push:
  pull_request:
permissions:
  contents: read

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install ".[dev]"
      - run: python -m pytest -v
      - run: python demo/mock_repair_demo.py

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t fr-harness:ci .
      - run: docker run -d --name fr-harness-ci -p 127.0.0.1:18000:8000 -e FR_LLM_BASE_URL=https://llm.invalid/v1 -e FR_LLM_MODEL=ci-model -e OPENAI_API_KEY=ci-placeholder fr-harness:ci
      - run: |
          for attempt in {1..30}; do
            curl --fail http://127.0.0.1:18000/ && break
            sleep 1
          done
          ! docker logs fr-harness-ci 2>&1 | grep -F "ci-placeholder"

  publish-image:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [unit-test, docker-build]
    permissions:
      contents: read
      packages: write
```

发布 job 登录 `ghcr.io`，用 `docker/metadata-action` 生成 `latest` 和 sha tag，再用 `docker/build-push-action` push。Dockerfile 的 OCI source label 固定指向公开仓库 URL。

- [ ] **Step 4: 本地验证并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_github_actions.py -v`

Run: `docker build -t fr-harness:remediation .`

Expected: 测试 PASS，Docker build 成功。

```powershell
git add .github/workflows/ci.yml Dockerfile README.md tests/test_github_actions.py temp/remediation-task-07
git commit -m "ci: add github verification and image publish"
```

---

### Task 8: OpenCode 两阶段独立评审与正式 PR

**Files:**
- Create: `temp/remediation-task-08/GOAL.md`
- Create: `temp/reviews/spec-compliance-review.md`
- Create: `temp/reviews/code-quality-review.md`
- Create: `temp/pr-body.md`
- Modify: `AGENT_LOG.md`

**Interfaces:**
- Consumes: 完整本地仓库、课程要求、OpenCode 1.17.18。
- Produces: 两份独立评审、确认问题的修复提交、GitHub PR。

- [ ] **Step 1: 创建 GOAL 并做提交前验证**

Run: `.\.venv\Scripts\python.exe -m pytest -v`

Run: `.\.venv\Scripts\python.exe demo/mock_repair_demo.py`

Run: `git grep -n -E "sk-[A-Za-z0-9_-]{20,}" -- . ":(exclude)A任务完成指南.md"`

Expected: 全量测试 PASS；演示恰好三行 PASS；凭据扫描无匹配。

- [ ] **Step 2: 运行 OpenCode 规格符合性评审**

使用新 `--pure` 会话和 `nju/deepseek-v4-flash`，要求它对照两份课程要求、SPEC、PLAN、源码和测试逐项输出 `Critical/Major/Minor`；发现证据不存在时必须标记缺失，不得替项目补写。将原始结论和人工判断写入 `temp/reviews/spec-compliance-review.md`。

Run:

```powershell
opencode run --pure --model nju/deepseek-v4-flash --dir . --file SPEC.md --file PLAN.md --file D:\SchoolProject\Summer\AI4SE_Final_Project_A_Coding_Agent_Harness.md --file D:\SchoolProject\Summer\通用要求.md "执行规格符合性评审。检查仓库代码和测试，但不要修改文件。逐项列出证据和 Critical/Major/Minor 问题；没有证据的历史流程不得推测为已完成。"
```

- [ ] **Step 3: 修复确认的规格问题**

逐条验证 OpenCode 指控。Critical/Major 且可复现的问题必须先加失败测试、运行红灯、最小修复、运行绿灯。误报或超出本轮范围的意见在评审文档写明理由。

- [ ] **Step 4: 运行独立代码质量评审**

开启另一个全新 `--pure` 会话，聚焦凭据泄漏、keyring 错误、配置优先级、路径/审批边界、并发/SQLite、CLI 输出、Docker/Actions 和测试缺口。将输出与人工判断写入 `temp/reviews/code-quality-review.md`，并按 TDD 修复确认的 Critical/Major。

- [ ] **Step 5: 提交评审修复并推送分支**

```powershell
git add AGENT_LOG.md temp/reviews temp/remediation-task-08
git commit -m "review: record specification and quality checks"
git push -u origin setup-scaffold
```

- [ ] **Step 6: 创建 PR**

PR base 为 `main`，标题为 `Complete FR-Harness implementation and delivery pipeline`。描述列出：Codex 主开发、OpenCode 两次独立评审、人工确认/修复、测试命令、Docker 命令、历史流程偏差。不得声称同账号批准了自己的 PR。

`temp/pr-body.md` 使用以下内容：

```markdown
## Summary

- Complete the handwritten FR-Harness agent loop, governance, feedback, memory, WebUI, CLI and distribution.
- Add OS-keyring credential lifecycle and declarative agent policy.
- Add GitHub Actions tests, Docker cold-start verification and GHCR publishing.

## Verification

- `python -m pytest -v`
- `python demo/mock_repair_demo.py`
- `docker build -t fr-harness:remediation .`

## AI and human ownership

Codex performed the main implementation. OpenCode ran independent specification-compliance and code-quality reviews. The repository owner selected the architecture, approved the remediation design and remains responsible for the final judgment. Early Tasks 1–12 did not consistently use a fresh subagent and two-stage review; the repository records that deviation instead of retroactively claiming it occurred.
```

Run: `gh pr create --base main --head setup-scaffold --title "Complete FR-Harness implementation and delivery pipeline" --body-file temp/pr-body.md`

创建后分别用 `gh pr comment` 发布规格评审和代码质量评审摘要，形成远程证据。

---

### Task 9: 获得真实 CI pass 并合并 PR

**Files:**
- Create: `temp/remediation-task-09/GOAL.md`
- Modify when needed: 被失败日志定位到的源码、测试或 workflow
- Modify: `AGENT_LOG.md`

**Interfaces:**
- Consumes: GitHub PR checks 与 Actions 日志。
- Produces: 真实绿色 PR checks、已合并 PR、绿色 main workflow。

- [ ] **Step 1: 创建 GOAL 并等待 PR checks**

Run: `gh pr checks --watch --interval 10`

Expected: `unit-test` 与 `docker-build` 均 PASS。若失败，使用 `gh run view <run-id> --log-failed` 获取根因。

- [ ] **Step 2: 按 systematic-debugging 修复真实失败**

每次只修复日志证明的根因；本地复现对应命令；提交并 push。重复检查直到绿色，不通过时不得合并。

- [ ] **Step 3: 合并**

Run: `gh pr merge --merge --delete-branch`

Expected: PR 状态 `MERGED`。随后：

Run: `git fetch origin`

Run: `git switch main`

Run: `git merge --ff-only origin/main`

- [ ] **Step 4: 验证 main**

Run: `gh run list --branch main --limit 5`

等待合并提交触发的 main 工作流完成；`unit-test`、`docker-build` 和 `publish-image` 必须 PASS。将 run URL、commit 和结果写入 AGENT_LOG，并提交/推送任何必要的证据更新时不得绕过 CI。

---

### Task 10: 发布并匿名验证公共容器镜像

**Files:**
- Create: `temp/remediation-task-10/GOAL.md`
- Modify: `README.md`
- Modify: `AGENT_LOG.md`
- Modify: `PLAN.md`

**Interfaces:**
- Consumes: GHCR main workflow 产物和 GitHub package visibility API。
- Produces: `ghcr.io/rippleorapple/fr-harness:latest` 公共镜像及匿名拉取证据。

- [ ] **Step 1: 创建 GOAL 并确认包存在**

Run: `gh api /user/packages/container/fr-harness`

Expected: 返回 package metadata。若 404，先检查 `publish-image` 日志，不猜测镜像已发布。

- [ ] **Step 2: 将 GHCR 包设为公开**

Run:

```powershell
gh api --method PATCH /user/packages/container/fr-harness/visibility -f visibility=public
```

Expected: visibility 为 `public`。如果当前 OAuth token 缺少 `write:packages`，不得输出或请求用户粘贴 token；准确记录 GitHub 权限阻塞，并让仓库所有者在 package settings 中执行一次 Public 设置。

- [ ] **Step 3: 使用空 Docker 配置匿名拉取**

在 `$env:TEMP` 下创建一个全新的空目录作为临时 `DOCKER_CONFIG`，确认解析后的绝对路径位于 `$env:TEMP` 后执行：

Run: `docker pull ghcr.io/rippleorapple/fr-harness:latest`

Expected: 不登录即可成功拉取。随后用 `docker image inspect` 验证 OCI source label 指向仓库。

- [ ] **Step 4: 更新最终文档并验证**

README 给出：

```bash
docker pull ghcr.io/rippleorapple/fr-harness:latest
docker run --rm -p 8000:8000 --env-file .env -v fr-harness-data:/data -v /absolute/project:/workspace/project:rw ghcr.io/rippleorapple/fr-harness:latest
```

PLAN/AGENT_LOG 写入真实 PR URL、Actions run URL、镜像 tag 和匿名拉取结论；不能写占位 URL。

Run: `.\.venv\Scripts\python.exe -m pytest -v`

Run: `.\.venv\Scripts\python.exe demo/mock_repair_demo.py`

Expected: 全量 PASS、三行演示 PASS。

- [ ] **Step 5: 最终证据提交**

在 main 上提交最终证据更新，push 后等待最后一次 GitHub Actions PASS。若该提交重新发布镜像，再次匿名拉取对应 latest。

```powershell
git add README.md PLAN.md AGENT_LOG.md temp/remediation-task-10
git commit -m "docs: record verified release evidence"
git push origin main
```

最终报告逐项标记十项“完成/受外部权限阻塞”，并提供 PR、CI、镜像和本地文件链接。
