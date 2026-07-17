# FR-Harness 实施计划

> **给智能体执行者：** 实施时必须逐个任务执行；优先使用 `superpowers:subagent-driven-development`，也可用 `superpowers:executing-plans`。每个任务都以复选框跟踪。

**目标：** 构建一个 Python Coding Agent Harness：在受限工作区内修改代码、运行 `pytest`、将客观失败结果回灌给 LLM，并将危险操作暂停等待用户审批。

**架构：** FastAPI 提供极简 WebUI；自建的 `Agent.run_once()` 负责读取任务状态、调用可注入 LLM、验证动作、执行护栏和工具、记录审计事件，并返回新的任务状态。SQLite 保存任务、审批、记忆和审计事件；MockLLM 使所有核心机制可以离线、确定性测试。

**技术栈：** Python 3.12、FastAPI、Uvicorn、Pydantic v2、SQLite、pytest、httpx、python-dotenv、Docker。

## 全局约束

- 仅支持 Python 工作区；修复的客观反馈信号是 `pytest`。
- 不得使用 LangChain、AutoGen、CrewAI、LlamaIndex Agent 或任何现成 Agent 主循环。
- 所有核心机制必须能在无网络、无真实模型时用 MockLLM 测试。
- 所有文件路径必须解析并限制在任务绑定的工作区根目录内。
- API Key 不得写入源码、SQLite、审计记录、日志或响应内容。
- 默认最多运行 8 轮；连续两次相同动作则任务失败。
- 危险操作必须经一次性人工批准后才能执行。
- 首版采用单进程、单任务执行；不做队列、并发或多 Agent。

## 项目结构

| 路径 | 职责 |
| --- | --- |
| `src/fr_harness/models.py` | 枚举、Pydantic 领域模型 |
| `src/fr_harness/db.py` | SQLite 初始化与仓储接口 |
| `src/fr_harness/llm.py` | LLM 协议、MockLLM、OpenAI 兼容适配器 |
| `src/fr_harness/guardrails.py` | 路径限制、危险动作分类、审批状态机 |
| `src/fr_harness/tools.py` | 受限文件读写与 pytest 工具分发 |
| `src/fr_harness/feedback.py` | pytest 输出解析与反馈摘要 |
| `src/fr_harness/memory.py` | 项目约定、失败尝试与上下文构建 |
| `src/fr_harness/agent.py` | 自建 Agent 主循环、停止策略 |
| `src/fr_harness/web.py` | FastAPI API 与任务/详情/审批页面 |
| `src/fr_harness/cli.py` | `init`、`serve`、`test` 命令 |
| `tests/` | 离线单元测试与 API 测试 |
| `demo/mock_repair_demo.py` | 必交的确定性机制演示 |
| `Dockerfile`、`.gitlab-ci.yml`、`README.md` | 分发、CI、使用说明 |

---

## 实现前强制关卡：陌生 Agent 冷启动验证 — 已补做并通过

> 课程要求此关卡必须在实现代码前完成。FR-Harness 已开始 Task 1–3 的实现，因此必须在继续 Task 4 前补做，并在 `SPEC_PROCESS.md` 中如实说明这是实施早期发现后补充的验证。

**目标：** 用一个与主开发 Agent 不同类型、没有此前对话和记忆的全新 Agent，检验 `SPEC.md` 与 `PLAN.md` 是否足以让陌生执行者开始工作。

- [x] 选择了不同类型的 OpenCode CLI Agent。
- [x] 创建了全新 `--pure` 会话，不导入此前历史或 memory。
- [x] 仅提供根目录 `SPEC.md` 与 `PLAN.md` 的副本。
- [x] 指定评估尚未实施的 Task 4 和 Task 6。
- [x] 要求其遇到不确定处停止，不得猜测实现。
- [x] 已在 `SPEC_PROCESS.md` 记录 Agent、隔离方式、首次暂停点和差异。
- [x] 已据首次反馈补充 SPEC §5.1 与 PLAN 的实现约定。
- [x] 第二次全新会话确认文档无阻塞歧义；允许继续 Task 4。

**通过标准：** 测试 Agent 能准确复述项目目标、识别 Task 4 的输入/输出/安全边界、找到正确文件路径；若不能，必须先修正文档而非开始编码。

**第一次验证结果与修订：** OpenCode（`nju/deepseek-v4-flash`，全新 `--pure` 会话）仅获提供 SPEC/PLAN 后，准确识别 Task 4/6 的目标，但因 ActionKind、Approval、GuardDecision、MemoryStore、SQLite schema 与 Chat 上下文格式缺失而停止。对应的规范性定义已补入 `SPEC.md` §5.1。

**第二次验证结果：** 另一个全新 `--pure` OpenCode 会话仅获更新后的 SPEC/PLAN，判定“可以开始”；它正确给出 Task 4 的路径逃逸/未批准测试，以及 Task 6 的 Chat role/最近两条记忆测试。无阻塞性歧义。

---

## Task 1：包基础与领域模型 — 已完成

**提交：** `915b27b feat: add domain models`
**文件：** `pyproject.toml`、`src/fr_harness/models.py`、`tests/test_models.py`

- [x] 先编写 `Action` 写文件动作与 `TaskStatus.PENDING_APPROVAL` 的失败测试。
- [x] 观察到 `fr_harness` 尚未实现导致的红灯。
- [x] 实现 `TaskStatus`、`ActionKind`、`ApprovalDecision`、`Action`、`Task`、`Feedback`、`ToolResult`。
- [x] 使用 `.venv\\Scripts\\python.exe -m pytest tests/test_models.py -v` 验证通过。

**已定义接口：**

```python
class Action(BaseModel):
    kind: ActionKind
    path: str | None
    content: str | None
    reason: str | None
```

## Task 2：SQLite 任务与审计持久化 — 已完成

**提交：** `82b1436 feat: persist tasks and audit events`
**文件：** `src/fr_harness/db.py`、`tests/test_db.py`

- [x] 先写任务创建/读取和审计事件按顺序保存的失败测试。
- [x] 实现 `Database.initialize()`，建立 `tasks`、`events`、`approvals`、`memory_entries` 表。
- [x] 实现 `create_task()`、`get_task()`、`append_event()`、`list_events()`。
- [x] 验证 Task 2 测试与完整测试均通过。

**已定义接口：**

```python
Database.create_task(goal: str, workspace: Path) -> Task
Database.get_task(task_id: UUID) -> Task
Database.append_event(task_id: UUID, kind: str, payload: dict[str, object]) -> None
Database.list_events(task_id: UUID) -> list[dict[str, object]]
```

## Task 3：可注入 LLM 接口 — 已完成

**提交：** `1b41219 feat: add injectable llm clients`
**文件：** `src/fr_harness/llm.py`、`tests/test_llm.py`

- [x] 先写 MockLLM 动作队列和 OpenAI 兼容响应解析的失败测试。
- [x] 实现 `LLMClient` 协议、`MockLLM`、`OpenAICompatibleLLM`。
- [x] 使用 `httpx.MockTransport` 离线验证真实适配器的响应解析；不记录 API Key。
- [x] 完整测试通过（当时为 7 passed）。

**已定义接口：**

```python
class LLMClient(Protocol):
    def next_action(self, context: list[dict[str, str]]) -> Action: ...
```

## Task 4：治理护栏与一次性审批状态机

**文件：** 新建 `src/fr_harness/guardrails.py`、`tests/test_guardrails.py`
**依赖：** Task 1

- [ ] 先写失败测试：`../secret.txt` 路径必须抛出 `ValueError("outside workspace")`；未批准的动作不可执行。
- [ ] 运行 `python -m pytest tests/test_guardrails.py -v`，确认因接口未实现而失败。
- [ ] 实现 `resolve_workspace_path(root, value)`：使用 `Path.resolve()`，任何非 `root` 子路径一律拒绝。
- [ ] 定义 `GuardDecision`：`allowed`、`requires_approval`、`blocked`。
- [ ] 规则：读取文件和新建文件可直接执行；覆盖已有文件、运行 pytest 需要审批；越界路径直接阻断。
- [ ] 实现 `ApprovalStateMachine`：`pending → approved → consumed` 或 `pending → rejected`；同一批准只能消费一次。
- [ ] 运行 Task 4 与完整测试；确认批准一次、拒绝永不执行、覆盖文件须审批。
- [ ] 提交：`git commit -m "feat: add guardrails and approval state machine"`。

**目标接口：**

```python
resolve_workspace_path(root: Path, value: str) -> Path
classify(action: Action, root: Path) -> GuardDecision
ApprovalStateMachine.create(kind: str, description: str) -> Approval
ApprovalStateMachine.can_execute(approval_id: UUID) -> bool
ApprovalStateMachine.approve(approval_id: UUID) -> None
ApprovalStateMachine.reject(approval_id: UUID) -> None
```

**实现约定：** `GuardDecision` 与 `Approval` 均定义在 `guardrails.py`；状态机为无数据库依赖的纯内存实现。必须用 `Path.resolve()` 防御 `..` 与符号链接逃逸；`write_file` 是否覆盖由已解析目标的 `exists()` 判定。

## Task 5：受限工具与 pytest 反馈解析

**文件：** 新建 `src/fr_harness/tools.py`、`src/fr_harness/feedback.py`、`tests/test_tools.py`、`tests/test_feedback.py`
**依赖：** Task 1、Task 4

- [ ] 先写失败测试：文件读取返回 UTF-8 内容；失败输出中提取 `FAILED test_app.py::test_greeting`。
- [ ] 实现 `parse_pytest_result(returncode, stdout, stderr) -> Feedback`：仅退出码 0 表示通过，摘要最长 2,000 字符。
- [ ] 实现 `ToolDispatcher.execute(action, workspace) -> ToolResult`，只允许读文件、写文件和运行 pytest。
- [ ] pytest 必须使用固定命令 `subprocess.run([sys.executable, "-m", "pytest", "-q"], ...)`，绝不能执行 LLM 给出的任意 shell 字符串。
- [ ] 运行测试并提交：`feat: add constrained tools and pytest feedback`。

## Task 6：记忆仓储与上下文构建

**文件：** 新建 `src/fr_harness/memory.py`、`tests/test_memory.py`
**依赖：** Task 1、Task 2

- [ ] 先写失败测试：上下文必须包含目标和最近失败尝试；`limit=2` 必须排除更早的记录。
- [ ] 实现 `MemoryStore.add()` 与 `MemoryStore.relevant()`，保存至 `memory_entries`。
- [ ] 实现 `build_context(goal, memories, feedback)`；顺序为系统安全约束、相关记忆、最近反馈、用户目标。
- [ ] 不保存或注入凭据。
- [ ] 运行测试并提交：`feat: add task memory context`。

**实现约定：** `MemoryStore(Database)` 接收数据库实例；`memory_entries` 字段为 `id`、`task_id`、`category`、`content`、`created_at`。上下文为 OpenAI Chat `list[dict[str, str]]`，前三类消息 role 为 `system`，最后的用户目标 role 为 `user`。

## Task 7：自建 Agent 主循环

**文件：** 新建 `src/fr_harness/agent.py`、`tests/test_agent.py`
**依赖：** Task 2、3、4、5、6

- [ ] 先写端到端失败测试：MockLLM 先写错代码、pytest 失败、获得反馈后修复、pytest 通过、最后才 `complete`。
- [ ] 实现 `Agent.run_once(task_id)` 和 `Agent.run_until_stopped(task_id)`。
- [ ] 每轮：构建上下文 → LLM 返回 `Action` → 校验并分类 → 护栏/审批 → 工具执行 → 审计与记忆 → 反馈回灌。
- [ ] 阻断动作使任务失败；危险动作创建审批并进入 `pending_approval`。
- [ ] 只有“pytest 通过后收到 `complete`”才可成功；超过 8 轮或连续两次相同动作则失败。
- [ ] 覆盖最大轮数、重复动作、路径阻断、失败测试后不能完成等测试；提交 `feat: add agent feedback control loop`。

## Task 8：持久化审批与恢复执行

**文件：** 修改 `db.py`、`agent.py`；新建 `tests/test_approvals_integration.py`
**依赖：** Task 2、4、5、7

- [ ] 先写失败测试：覆盖已有文件在批准前不得写入；批准后仅执行一次。
- [ ] 实现 `create_approval()`、`decide_approval()`、`get_pending_approval()`。
- [ ] `resume_after_approval()` 必须原子消费已批准动作，执行并写审计；拒绝则任务 `cancelled`。
- [ ] 测试拒绝、一次性消费、SQLite 重启后仍能读取待审批项；提交 `feat: persist approval workflow`。

## Task 9：FastAPI 与三页极简 WebUI

**文件：** 新建 `src/fr_harness/web.py`、`tests/test_web.py`
**依赖：** Task 2、3、7、8

- [ ] 先写失败 API 测试：`POST /tasks` 重定向至任务页；审批拒绝接口返回 303。
- [ ] 实现 `create_app(database_path, llm) -> FastAPI`。
- [ ] `GET /` 为任务创建页；`GET /tasks/{id}` 显示状态和转义后的审计 JSON；`GET /approvals` 列出待审批项。
- [ ] 实现批准/拒绝 POST 路由；工作区必须存在且为目录；页面绝不展示 key。
- [ ] 运行 API 测试并提交：`feat: add task and approval web ui`。

## Task 10：CLI、安全配置与 Docker 分发

**文件：** 修改/新建 `cli.py`、`Dockerfile`、`.dockerignore`、`.env.example`、`tests/test_cli.py`
**依赖：** Task 2、3、9

- [ ] 先写失败测试：`init` 创建数据库，标准输出不得含 `OPENAI_API_KEY`。
- [ ] 实现 `python -m fr_harness.cli init|serve|test`。
- [ ] `serve` 仅从环境读取 `FR_DATABASE_PATH`、`FR_LLM_BASE_URL`、`FR_LLM_MODEL`、`OPENAI_API_KEY`，不记录其值。
- [ ] Docker 基于 `python:3.12-slim`，暴露 8000，启动 Uvicorn；`.dockerignore` 排除 `.git`、`.env`、`.venv`、缓存和 SQLite。
- [ ] 运行 `docker build -t fr-harness:local .` 并提交 `feat: add cli and docker distribution`。

## Task 11：MockLLM 机制演示

**文件：** 新建 `demo/mock_repair_demo.py`、`tests/test_demo.py`
**依赖：** Task 7、8

- [ ] 测试必须执行演示脚本，并断言退出码为 0。
- [ ] 脚本只用 `TemporaryDirectory`、临时 pytest 项目和 MockLLM；不得读取真实 key 或发网络请求。
- [ ] 输出三行：`guardrail approval: PASS`、`feedback repair: PASS`、`approval one-time use: PASS`。
- [ ] 运行 `python demo/mock_repair_demo.py` 与测试后，提交 `test: add deterministic mechanism demo`。

## Task 12：CI、README 与发布验证

**文件：** 修改 `.gitlab-ci.yml`、`README.md`；新建 `tests/test_readme_security.py`
**依赖：** Task 10、11

- [ ] 先写 README 失败测试，要求包含 `OPENAI_API_KEY`、`.env`、`明文`、`docker build`。
- [ ] CI 必须有名为 `unit-test` 的 job，安装 `.[dev]` 后运行 `python -m pytest -v`；可选增加镜像构建 job。
- [ ] README 必须用 UTF-8，说明项目、架构、安装、测试、WebUI、Mock 演示、Docker、Key 安全、`.env` 明文风险、工作区边界、限制和目录结构。
- [ ] 完整运行 `python -m pytest -v`、`python demo/mock_repair_demo.py`、Docker 冷启动验证；提交 `docs: add release and security guide`。

## 依赖关系与可并行项

| 任务 | 前置任务 | 可在独立分支并行 |
| --- | --- | --- |
| 1 | 无 | 否（已完成） |
| 2 | 1 | 否（已完成） |
| 3 | 1 | 是（已完成） |
| 4 | 1 | 是 |
| 5 | 1、4 | 否 |
| 6 | 1、2 | 是 |
| 7 | 2、3、4、5、6 | 否 |
| 8 | 2、4、5、7 | 否 |
| 9 | 2、3、7、8 | 否 |
| 10 | 2、3、9 | 否 |
| 11 | 7、8 | 是 |
| 12 | 10、11 | 否 |

## 完成前检查

- 每一项功能都先有失败测试，并实际观察红灯。
- 每个任务完成后运行完整测试、做规约与代码质量审查，并记录到 `AGENT_LOG.md`。
- 提交历史不得含真实凭据；`git status --short` 只应出现预期文件。
- 不得在测试通过前宣称完成；最终 CI 必须为 pass。
