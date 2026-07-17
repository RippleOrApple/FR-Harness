# FR-Harness

FR-Harness 是一个小而完整的 Python Coding Agent Harness。用户提交代码修复目标后，它在绑定的本地工作区内读取或修改文件、运行 `pytest`，把客观失败结果回灌给 LLM，并在危险动作前暂停等待人工审批。

项目的重点是自己实现并验证 Agent 控制循环，而不是套用 LangChain、AutoGen、CrewAI 等现成 Agent runner。所有核心机制都可以用 `MockLLM` 离线、确定性测试。

## 核心能力

- 自建 `Agent.run_once()` / `run_until_stopped()` 反馈控制循环。
- 结构化动作：读文件、写文件、运行 pytest、申请审批、声明完成。
- 工作区路径约束，防御 `..` 和符号链接逃逸。
- 覆盖已有文件和运行 pytest 前的持久化人工审批。
- SQLite 任务、审计、审批和记忆持久化。
- pytest 失败节点与摘要回灌；只有最近一次 pytest 通过后才允许成功。
- 最大 8 轮、连续重复动作和阻断动作停止策略。
- 操作系统 keyring 凭据生命周期和声明式 Agent 规则。
- 三页 FastAPI WebUI、CLI、GitLab CI 与 Docker 分发。

## 架构

```text
WebUI / CLI
  -> HarnessConfig（TOML + 受控环境覆盖）
  -> Agent 控制循环
  -> LLMClient（MockLLM / OpenAICompatibleLLM）
  -> 护栏分类与 SQLite 审批
  -> 受限 ToolDispatcher
       |- UTF-8 文件读取
       |- UTF-8 文件写入
       `- 固定命令 python -m pytest -q
  -> Feedback / Memory / Audit
  -> SQLite

Credential source: 环境变量优先 -> system keyring
```

任务状态通常按以下路径变化：

```text
created -> running -> pending_approval -> running -> succeeded
                  |                    |          `-> failed
                  |                    `-> cancelled（拒绝审批）
                  `-> failed
```

## 环境要求

- Python 3.12 或更高版本
- Git
- 可选：Docker Desktop / Docker Engine（容器运行）
- 可选：OpenAI 兼容 Chat Completions 服务（真实模型运行）

核心测试和演示不需要网络或真实模型。

## 本地安装

```bash
python -m venv .venv
```

PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

macOS/Linux：

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

初始化默认数据库：

```bash
python -m fr_harness.cli init
```

也可以指定位置：

```bash
python -m fr_harness.cli init --database ./state/fr.sqlite3
```

## 配置真实模型

真实模型 endpoint 和 model 从进程环境读取；API key 按“环境变量优先 → system keyring”解析：

| 变量 | 作用 | 示例类型 |
| --- | --- | --- |
| `FR_DATABASE_PATH` | SQLite 路径 | `./state/fr.sqlite3` |
| `FR_LLM_BASE_URL` | OpenAI 兼容 API 基础 URL | 供应商提供的 `/v1` 地址 |
| `FR_LLM_MODEL` | 模型标识 | 供应商提供的模型名 |
| `OPENAI_API_KEY` | 容器/CI 的凭据来源 | 由平台 Secret 注入 |

本地交互使用推荐把 key 存入 system keyring：

```bash
python -m fr_harness.cli credential set
python -m fr_harness.cli credential status
```

录入使用隐藏输入。Windows 使用 Windows Credential Manager；macOS 使用 Keychain；Linux 需要可用的 Secret Service。状态命令只显示 `environment`、`system keyring` 或未配置，不回显 key。更新和清除分别使用：

```bash
python -m fr_harness.cli credential update
python -m fr_harness.cli credential clear
```

如果没有任何凭据，交互式 `serve` 会引导隐藏录入并保存；非交互式运行会提示先执行 `credential set`。

`.env` 只作为容器或兼容回退，可以从模板开始：

```powershell
Copy-Item .env.example .env
```

填好后，让当前进程安全地获得这些变量，再启动服务。项目会调用 `python-dotenv` 读取本地 `.env`，但不会打印配置值。

> `.env` 是明文文件，不是秘密保险箱。它可能被本机管理员、恶意进程、备份工具或误配置的同步软件读取。务必限制文件权限，保持 `.env` 在 `.gitignore` 中，绝不提交到 Git；生产环境应优先使用平台 Secret Manager 或短期凭据。

### 声明式 Agent 规则

根目录 `fr-harness.toml` 只保存非秘密规则：

```toml
[agent]
max_iterations = 8
memory_limit = 5

[approvals]
existing_file_write = true
run_pytest = true
```

可用 `FR_CONFIG_PATH` 指向另一份 TOML；`FR_MAX_ITERATIONS`、`FR_MEMORY_LIMIT`、`FR_APPROVE_EXISTING_WRITE`、`FR_APPROVE_PYTEST` 可覆盖对应值。工作区越界始终阻断，不能通过配置关闭。任何 API key 都不得写入 `fr-harness.toml`。

OpenAI 兼容服务返回的消息内容必须是一个符合 `Action` 模型的 JSON 对象，例如：

```json
{"kind":"read_file","path":"app.py"}
```

## WebUI

配置环境变量后启动：

```bash
python -m fr_harness.cli serve
```

默认监听 `0.0.0.0:8000`。浏览器访问 `http://localhost:8000/`：

1. 在“新建任务”页填写目标和现存工作区目录。
2. 在任务详情页查看状态、轮次和转义后的审计 JSON。
3. 在“待审批”页批准或拒绝危险动作。

首版是单进程同步执行；创建任务的 HTTP 请求会运行到成功、失败或等待审批为止。

## CLI

```text
python -m fr_harness.cli init [--database PATH]
python -m fr_harness.cli serve [--host HOST] [--port PORT]
python -m fr_harness.cli test
python -m fr_harness.cli credential set
python -m fr_harness.cli credential status
python -m fr_harness.cli credential update
python -m fr_harness.cli credential clear
```

`test` 子命令固定执行当前解释器的 `python -m pytest -v`，不会接受或拼接任意 shell 命令。

## 测试与 MockLLM 演示

完整测试：

```bash
python -m pytest -v
```

也可以通过 CLI：

```bash
python -m fr_harness.cli test
```

确定性核心机制演示：

```bash
python demo/mock_repair_demo.py
```

预期输出：

```text
guardrail approval: PASS
feedback repair: PASS
approval one-time use: PASS
```

演示只使用 `TemporaryDirectory`、临时 pytest 项目、SQLite 和 `MockLLM`，不读取真实 key，也不访问网络。

## Docker

构建镜像：

```bash
docker build -t fr-harness:local .
```

公共 GHCR 镜像可匿名拉取：

```bash
docker pull ghcr.io/rippleorapple/fr-harness:latest
```

镜像包页面：https://github.com/RippleOrApple/FR-Harness/pkgs/container/fr-harness

2026-07-17 的交付验证使用全新空 `DOCKER_CONFIG` 完成真实 pull，得到 manifest digest
`sha256:ba7b5dd3022bcca178e6749468cdbcad43e80b25f636a0103851adfece4c7012`；随后冷启动返回 HTTP 200，容器日志中的注入测试凭据匹配为 0。该验证不复用本机 Docker 登录状态。

准备 `.env` 后运行，并同时挂载持久化数据和待修复工作区：

```bash
docker run --rm \
  -p 8000:8000 \
  --env-file .env \
  -v fr-harness-data:/data \
  -v /absolute/path/to/project:/workspace/project:rw \
  fr-harness:local
```

在 Web 表单中填写容器内路径 `/workspace/project`，而不是宿主机路径。镜像默认把数据库写到 `/data/fr_harness.sqlite3`。

容器不依赖桌面 system keyring。再次提醒：`--env-file .env` 会把明文凭据注入容器进程环境。不要把 `.env` 烘焙进镜像或提交到仓库；有条件时使用容器平台 Secret 的挂载或注入能力。

## 安全模型

- `OPENAI_API_KEY` 不得进入源码、Git 历史、SQLite、审计事件、页面或日志。
- 本地 key 存入 system keyring；环境变量优先级只用于显式的容器、CI 或运维覆盖。
- 任务目标、记忆、反馈、动作审计和审批 JSON 在持久化前会对常见 key/token/secret 赋值及 OpenAI 风格 key 做脱敏。
- 文件路径通过解析后的工作区根目录检查；工作区外访问直接阻断并使任务失败。
- 读文件和新建文件可直接执行；覆盖已有文件与运行 pytest 默认要求一次性审批。
- 批准采用 SQLite 条件更新从 `approved` 原子变为 `consumed`，同一动作不会重复执行。
- pytest 只能使用固定参数数组 `[sys.executable, "-m", "pytest", "-q"]`，`shell=False`。
- WebUI 会 HTML 转义目标与审计 JSON，但首版没有登录鉴权，不应直接暴露到不可信网络。

## 工作区边界

每个任务创建时绑定一个现存目录。文件动作会把相对路径和根目录分别 `resolve()`，只有解析后仍位于根目录内才会执行。因此 `../secret.txt` 和指向工作区外部的符号链接都会被拒绝。

容器中只能选择已挂载进容器的目录。请使用最小范围的读写挂载，不要把整个用户主目录或系统盘作为工作区。

## CI

`.gitlab-ci.yml` 包含两个阶段：

- `unit-test`：在 Python 3.12 镜像中安装 `.[dev]` 并运行 `python -m pytest -v`。
- `docker-build`：测试通过后使用 Docker-in-Docker 构建提交镜像。

`.github/workflows/ci.yml` 在每次 push 和 PR 运行：

- `unit-test`：Python 3.12 全量测试和 MockLLM 机制演示。
- `docker-build`：构建镜像、冷启动、HTTP 200 和日志无测试凭据检查。
- `publish-image`：仅 main 的前两项通过后，发布 `ghcr.io/rippleorapple/fr-harness:latest` 和 commit SHA tag。

GHCR 包发布成功不自动等于“公共镜像”；最终交付还必须把 package visibility 设为 Public，并用未登录的空 Docker 配置匿名拉取验证。

## 项目结构

```text
src/fr_harness/
  agent.py       # 自建控制循环与停止策略
  cli.py         # init / serve / test / credential
  config.py      # TOML 声明式 Agent 规则
  credentials.py # system keyring 凭据生命周期
  db.py          # SQLite 任务、事件和审批仓储
  feedback.py    # pytest 反馈解析
  guardrails.py  # 路径限制与治理分类
  llm.py         # MockLLM / OpenAI 兼容客户端
  memory.py      # 任务记忆和上下文
  models.py      # Pydantic 领域模型
  security.py    # 凭据脱敏
  tools.py       # 受限工具分发
  web.py         # FastAPI 三页 WebUI
demo/
  mock_repair_demo.py
tests/
temp/*/          # 每个实施 Task 的 GOAL 与过程记录
fr-harness.toml
Dockerfile
.gitlab-ci.yml
.github/workflows/ci.yml
SPEC.md
PLAN.md
SPEC_PROCESS.md
AGENT_LOG.md
REFLECTION.md
```

## 已知限制

- 只支持 Python 项目，并只把 pytest 作为客观反馈信号。
- 单进程、单任务同步执行，没有后台 worker、任务队列或并发控制。
- 没有多 Agent、向量检索、IDE 插件、用户认证或生产级权限系统。
- 真实模型必须可靠地产生结构化 Action JSON；首版没有宽松的自然语言解析器。
- 凭据脱敏是防御层，不替代 Secret Manager、最小权限和提交前扫描。
- 批准消费保证危险动作“至多一次”；SQLite 状态与文件系统副作用无法构成跨系统原子事务。

## 课程过程文件

`SPEC.md`、`PLAN.md` 和 `SPEC_PROCESS.md` 记录需求、实施计划和陌生 Agent 冷启动验证；`AGENT_LOG.md` 与 `temp/task-*/` 记录实现证据。`REFLECTION.md` 的最终个人反思必须由学生根据真实过程自行撰写。
