# FR-Harness 设计规约

**日期：** 2026-07-17  
**状态：** 已批准；补救实施中  
**项目类型：** AI4SE A 路线——Coding Agent Harness

## 1. 问题陈述

FR-Harness 面向希望让 LLM 在本地 Python 项目中执行小型修复、但不愿把文件系统和测试执行权无条件交给模型的开发者。成熟 Coding Agent 很强，但其内部治理、反馈和状态机通常不透明；课程项目需要一套可以阅读、离线测试和解释的最小 Harness 内核。

用户提交修复目标和工作区后，系统组织上下文、调用可注入 LLM、解析结构化动作、执行受限工具、把 `pytest` 的客观结果回灌，并在危险动作前等待人工审批。价值不在复刻通用编码智能体，而在提供一个可验证的参考实现：移除真实 LLM 后，治理、工具、反馈、记忆和停机机制仍可确定性测试。

### 1.1 目标用户

- 学习 Agent 工程、需要观察控制循环与审计证据的开发者。
- 希望在受限目录内试验自动修复、并保留人工最终控制权的 Python 项目维护者。
- 需要比较“提示词约束”和“代码护栏”差别的课程评审者。

### 1.2 范围

首版支持单进程、单任务、Python + `pytest`、FastAPI 极简 WebUI、SQLite、CLI、OpenAI 兼容 API、MockLLM、Docker 与 CI。不包含多 Agent、后台队列、任意 shell、IDE 插件、用户认证、多租户或语义向量检索。

## 2. 用户故事

### US-1：受限修复任务

作为 Python 开发者，我希望提供目标和一个现存工作区，让 Agent 只在该目录内读写和运行固定的 `pytest`，从而避免访问其他文件。故事独立、可测试，最小交付是创建任务后得到终态或待审批状态。

### US-2：危险动作审批

作为审批者，我希望覆盖已有文件或运行测试前看到具体动作并明确批准或拒绝，使副作用不能只凭模型意愿发生。一次批准只能消费一次，拒绝后动作不可恢复。

### US-3：客观反馈纠错

作为维护者，我希望失败测试名和精简错误摘要进入下一轮上下文，使 Agent 根据确定性信号改变动作，而不是自称“已完成”。只有最近一次 `pytest` 通过后，`complete` 才能成功。

### US-4：安全管理 API key

作为操作者，我希望用隐藏输入把 key 存入操作系统 keyring，并能查看配置状态、更新或清除；状态、错误、日志和数据库均不得回显明文。

### US-5：从公开镜像运行

作为新用户，我希望从 GHCR 拉取公开 Docker 镜像，挂载自己的项目和数据卷，并通过环境变量或平台 Secret 注入自己的 key，在不构建源码的情况下启动 WebUI。

### US-6：离线验证核心机制

作为评审者，我希望一条命令运行 MockLLM 单元测试和机制演示，不依赖网络或付费 API，以客观复查项目确实自行编码了 Harness。

## 3. 功能规约

### 3.1 模块契约

| 模块 | 输入 | 行为 | 输出 | 边界条件 | 错误处理 |
|---|---|---|---|---|---|
| `models.py` | 动作、任务、反馈字段 | 用 Pydantic 校验领域对象 | `Action`、`Task`、`Feedback` | 动作类型固定为五种 | 非法结构抛验证错误 |
| `llm.py` | Chat 消息列表 | Mock 队列取动作或单次调用 OpenAI 兼容 API | 一个结构化 `Action` | 不提供高层 Agent runner | HTTP/JSON 错误由主循环归一为失败 |
| `guardrails.py` | `Action`、工作区、审批策略 | 解析路径并分类 allowed / approval / blocked | `GuardDecision` | 路径逃逸永远 blocked | 越界不执行，主循环记录阻断 |
| `tools.py` | 允许执行的 Action | UTF-8 读写或固定参数运行 pytest | `ToolResult` | 不接受任意 shell；路径限工作区 | 参数或 I/O 错误由主循环记录 |
| `feedback.py` | pytest 退出码和双流输出 | 提取失败节点并截断摘要 | `Feedback` | 摘要上限 2,000 字符 | 无输出时生成退出码摘要 |
| `memory.py` | task id、分类、文本、limit | 脱敏持久化并按最新优先检索 | 相关记忆与 Chat context | 默认最多 5 条 | limit 小于 1 返回空 |
| `db.py` | 任务、事件、审批 | SQLite 事务和条件更新 | 持久状态与审计列表 | 一次性审批用 compare-and-set | 未知 id 抛 `KeyError`，冲突抛 `ValueError` |
| `agent.py` | Database、LLM、配置、工具 | 手写控制循环、停机和恢复 | 新任务状态 | 默认最多 8 轮；重复动作停止 | 异常转成脱敏失败事件 |
| `credentials.py` | keyring backend、环境 | 安全读写 key，环境变量优先解析 | key 或配置来源 | 不写数据库/配置/日志 | 后端异常转成固定通用错误 |
| `config.py` | TOML 与允许的环境覆盖 | 加载非秘密声明式规则 | `HarnessConfig` | 正数范围、安全审批默认 | 非法值快速失败 |
| `web.py` | HTTP 表单与审批决定 | 创建任务、显示转义日志、恢复审批 | HTML/303/4xx | 工作区必须是现存目录 | 400/404/409，不显示秘密 |
| `cli.py` | init/serve/test/credential 参数 | 初始化、启动、测试和 key 生命周期 | 退出码与非秘密提示 | 测试命令固定，录入隐藏 | 配置缺失返回 2 |

### 3.2 规范性领域接口

- `ActionKind` 固定为 `read_file`、`write_file`、`run_pytest`、`request_approval`、`complete`。
- `Action` 字段为 `kind`、`path`、`content`、`reason`。
- `GuardDecision` 为 `allowed`、`requires_approval`、`blocked`。
- `resolve_workspace_path(root, value)` 对根和候选路径调用 `Path.resolve()`；候选不是根的子路径时抛 `ValueError("outside workspace")`。
- `classify(action, root, policy)`：读文件允许；新建文件允许；覆盖已有文件和运行 pytest 默认需审批；越界始终阻断。
- `MemoryStore.relevant(task_id, limit)` 按数据库 id 倒序返回至多 limit 条。
- `build_context(goal, memories, feedback)` 顺序为安全 system、记忆 system、最近反馈 system、目标 user。
- `Agent.run_once()` 每轮只取得一个动作；`run_until_stopped()` 在成功、失败、取消或待审批时停止。

### 3.3 CLI

```text
python -m fr_harness.cli init [--database PATH]
python -m fr_harness.cli serve [--host HOST] [--port PORT]
python -m fr_harness.cli test
python -m fr_harness.cli credential set
python -m fr_harness.cli credential status
python -m fr_harness.cli credential update
python -m fr_harness.cli credential clear
```

`set` 不覆盖已有 keyring 值；`update` 要求已有值；`clear` 幂等；`status` 只显示来源和是否配置。`serve` 先要求 endpoint 和 model，再按环境变量、keyring 顺序解析 key；交互式首次运行可隐藏录入，非交互环境给出命令提示。

## 4. 非功能性需求

### 4.1 性能

- 单任务控制循环默认不超过 8 次 LLM 决策。
- 单次上下文默认最多注入 5 条记忆，pytest 摘要不超过 2,000 字符。
- SQLite 和 WebUI 面向课程级单用户负载；不承诺并发 worker 吞吐。

### 4.2 安全

- key 不得进入源码、Git 历史、SQLite、审计、响应、日志或终端 history。
- 文件操作必须通过解析后的工作区边界。
- pytest 使用参数数组 `[sys.executable, "-m", "pytest", "-q"]` 且 `shell=False`。
- 危险动作必须经持久化、一次性人工审批。
- 所有用户可见 HTML 和 JSON 文本进行脱敏/转义。

### 4.3 可用性

- 本地 CLI 在缺少 key 时给出下一条可执行命令。
- README 同时给出源码安装、Docker 获取、工作区挂载和凭据配置。
- Mock 演示无需网络，在临时目录内自清理。

### 4.4 可观测性

- 任务状态、轮次、动作、工具结果、反馈、审批和停止原因写入 SQLite 事件。
- WebUI 任务详情展示 HTML 转义后的审计事件。
- CI 运行测试、演示、Docker build 和冷启动；失败日志不得含 key。

### 4.5 可移植性

- Python 3.12 或更高；开发验证覆盖 Windows，容器目标为 Linux amd64/arm64 兼容的 `python:3.12-slim` 用户空间。
- keyring 使用操作系统可用后端；无桌面 keyring 的 Docker/CI 使用环境变量或平台 Secret。

## 5. 系统架构

```text
CLI / FastAPI WebUI
        |
        v
  Agent handwritten loop ---- HarnessConfig
        |
        +---- LLMClient ---- MockLLM / OpenAI compatible endpoint
        |
        +---- Guardrails ---- persisted one-time approval
        |
        +---- ToolDispatcher ---- files / fixed pytest
        |
        +---- Feedback + Memory + Audit events
                              |
                            SQLite

Credential source: process environment -> OS keyring
Distribution: GitHub -> Actions -> GHCR Docker image
```

外部依赖只有 OpenAI 兼容 Chat Completions 服务、操作系统 keyring、pytest 与 Docker/GitHub 基础设施。核心离线测试不访问这些外部网络服务。

任务状态：

```text
created -> running -> pending_approval -> running -> succeeded
                  |                    |          -> failed
                  |                    -> cancelled
                  -> failed
```

## 6. 数据模型

| 实体 | 主要字段 | 关系与约束 |
|---|---|---|
| Task | id UUID、goal、workspace、status、iteration | 工作区为解析后的绝对路径；iteration 非负 |
| Event | id、task_id、kind、payload、created_at | 归属 Task；按 id 追加读取；payload 为脱敏 JSON |
| Approval | id UUID、task_id、action_json、decision、created_at | decision 为 pending/approved/rejected/consumed；approved 仅能原子消费一次 |
| MemoryEntry | id、task_id、category、content、created_at | 归属 Task；内容写入前脱敏 |
| Action | kind、path、content、reason | kind 决定必需字段；不会独立持久化秘密 |
| Feedback | passed、summary、failed_tests | passed 仅由 pytest 退出码决定 |

SQLite 表为 `tasks`、`events`、`approvals`、`memory_entries`。首版不做 schema migration 框架和跨数据库支持。

## 7. 凭据与分发设计

### 7.1 凭据生命周期

- 安全存储：Python `keyring` 连接 Windows Credential Manager、macOS Keychain 或 Linux Secret Service。
- 首次录入：`credential set` 或交互式 `serve` 使用 `getpass` 隐藏输入。
- 查看：`credential status` 只显示 `environment`、`system keyring` 或未配置。
- 更新：`credential update` 替换 keyring 条目。
- 清除：`credential clear` 删除 keyring 条目且可重复执行。
- 运行时优先级：`OPENAI_API_KEY` 环境变量优先，随后系统 keyring。
- `.env` 仅为兼容来源，是明文且进程环境可见；不得提交。容器优先使用平台 Secret，课程演示可用受保护的 env file。

### 7.2 凭据威胁模型

| 威胁 | 攻击面/资产 | 控制 | 剩余风险 |
|---|---|---|---|
| 源码或 Git 泄漏 | API key | 禁止硬编码、忽略 `.env`、提交前扫描 | 已泄漏历史需供应商轮换，脱敏无法撤回 |
| shell history | 命令行 key | 隐藏交互录入，不要求命令行传值 | 本机键盘记录器仍可窃取 |
| `.env` 明文 | 本地磁盘/备份 | 文档警告、gitignore、最小文件权限 | 本机管理员和恶意进程可读 |
| 进程环境 | 环境变量 | 本地优先 keyring，容器用平台 Secret | 同权限进程/调试器可能读取 |
| 日志/审计 | 动作、目标、错误 | 写入前脱敏；固定通用 keyring 错误 | 未识别的新 key 格式可能绕过模式 |
| WebUI | 目标和审计 | HTML 转义、内容脱敏 | 首版无登录，不能暴露到不可信网络 |
| 容器层/上下文 | key 和本地文件 | `.dockerignore`，不使用构建参数传 key | 运行时环境仍对容器内进程可见 |
| 工作区逃逸 | 用户文件 | `Path.resolve()` 后检查子路径 | 有权限的宿主进程不受本应用沙箱约束 |
| keyring 不可用 | 可用性和错误 | 通用错误、环境变量回退 | 无 Secret Service 的 Linux 需外部配置 |

### 7.3 分发

- 源码：公开 GitHub 仓库。
- 容器：`ghcr.io/rippleorapple/fr-harness:latest`，由 main 分支 GitHub Actions 发布；公共性必须以匿名拉取验证。
- 本地构建：`docker build -t fr-harness:local .`。
- 运行需要挂载 `/data` 和最小范围工作区，并通过环境变量/平台 Secret 提供真实模型配置。

## 8. 技术选型与理由

| 选择 | 理由 |
|---|---|
| Python 3.12 | 与 pytest coding 场景一致，标准库有 SQLite/TOML，类型与测试生态成熟 |
| FastAPI | 用少量代码提供任务、详情、审批三页接口；不引入前端构建链 |
| SQLite | 单用户、单进程下零服务依赖，适合持久化状态机和审计 |
| Pydantic v2 | 严格验证结构化动作和配置 |
| OpenAI 兼容 API | 只使用底层单次补全，可切换供应商，不借用 Agent runner |
| MockLLM | 使控制循环和机制完全离线、确定性测试 |
| keyring | 跨平台连接系统安全存储，不自造密码学 |
| Docker + GHCR | 单一可复现运行形态，公开 registry 与 GitHub CI 集成直接 |
| GitHub Actions + GitLab CI 文件 | GitHub 仓库获得真实 CI；同时满足课程最终清单的 `unit-test` job |

WebUI 仅为服务器渲染的极简管理页，不做视觉创作或组件系统，因此豁免 Open Design；安全与机制优先。

## 9. 验收标准

| 功能 | 客观完成条件 | 证据 |
|---|---|---|
| 手写主循环 | 失败反馈改变下一动作，测试通过后才成功 | `tests/test_agent.py` |
| 路径与审批 | 越界阻断，危险动作暂停，批准只消费一次 | `tests/test_guardrails.py`、`tests/test_approvals_integration.py` |
| 凭据生命周期 | fake keyring 下 set/status/update/clear，输出无秘密 | `tests/test_credentials.py` |
| 记忆与上下文 | task 隔离、limit、固定消息顺序、脱敏 | `tests/test_memory.py` |
| WebUI | 创建、详情转义、审批/拒绝路由 | `tests/test_web.py` |
| 机制演示 | 输出恰好三行 PASS，离线临时运行 | `demo/mock_repair_demo.py`、`tests/test_demo.py` |
| 一键测试 | `python -m pytest -v` 全部通过 | 本地与 GitHub Actions run |
| 容器 | build、冷启动、HTTP 200、日志无测试 key | Docker 命令与 CI `docker-build` |
| 分发 | main 发布 GHCR，空 Docker 配置可匿名 pull | Actions run 与匿名拉取记录 |
| 文档 | SPEC/PLAN/过程/README 与实现一致 | `tests/test_course_documents.py`、人工 review |

## 10. 风险与未决问题

| 风险或未决问题 | 决策/对策 |
|---|---|
| LLM 返回非 JSON 或错误动作 | Pydantic 校验并将任务失败；首版不做宽松自然语言修复 |
| SQLite 状态和文件副作用非跨系统原子 | 一次性 consume 保证至多一次，不承诺 exactly-once |
| 同步 Web 请求运行任务可能耗时 | 首版范围接受；后台 worker 留作后续 |
| WebUI 无认证 | 只绑定可信网络；公开云部署前必须增加认证和隔离 |
| keyring 后端因平台不可用 | 给出通用错误和环境/平台 Secret 回退 |
| GHCR 默认包可见性可能为 private | 发布后显式改 Public 并做匿名拉取；权限不足时标记未完成 |
| 历史流程没有逐 task subagent 和双评审 | 如实记录偏差；当前补救使用 OpenCode 独立评审，不倒签 |
| 任意项目执行 pytest 仍可能运行恶意代码 | 运行前审批；用户只选择可信工作区；未来可加入容器沙箱 |

## 11. 领域与机制设计

### 11.1 动作 / 工具

允许读取 UTF-8 文件、新建或覆盖 UTF-8 文件、运行固定 pytest、请求审批和声明完成。不提供通用 shell 或任意命令拼接。动作由 Pydantic 代码校验，工具分发由 `ToolDispatcher` 明确枚举。

### 11.2 客观反馈信号

`pytest` 退出码决定 passed；解析器提取失败 node id 和至多 2,000 字符摘要，持久化并回灌下一轮。模型声明不能覆盖客观失败。MockLLM 演示先失败、后改变写入、再通过。

### 11.3 危险动作

路径逃逸直接阻断；覆盖已有文件和运行 pytest 默认进入 `pending_approval`。审批存入 SQLite，只有从 approved 原子转为 consumed 的调用能执行一次。拒绝导致取消。声明式配置可在受控场景关闭某类审批，但不能关闭工作区阻断。

### 11.4 记忆

记忆保存当前任务相关的失败摘要和工具结果，写入前脱敏，按最新优先限制条数。上下文只注入当前 task 的相关片段，不全量加载历史。

### 11.5 决策与配置

`Agent.run_once()` 自行完成上下文 → LLM → 动作 → 护栏 → 工具 → 反馈 → 停机。`fr-harness.toml` 声明迭代、记忆和审批策略；内容不含秘密。

### 11.6 主要贡献：治理

治理是本项目做深的维度：解析后路径围栏、动作分类、持久化 HITL、一次性审批消费、拒绝/取消状态、脱敏审计与可配置安全默认共同形成代码机制。移除真实 LLM 后，`tests/test_guardrails.py`、`tests/test_approvals_integration.py` 和机制演示仍能证明它工作，因此不是提示词约束。
