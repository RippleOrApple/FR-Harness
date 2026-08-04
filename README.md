# FR-Harness

FR-Harness 是一个面向 Python 项目的安全 Coding Agent Harness。它在用户指定的工作区内读取和修改文件，以 `pytest` 作为客观反馈，并在覆盖已有文件等危险操作前暂停等待审批。Agent 控制循环、状态恢复、护栏、审计和记忆均由项目自行实现。

## 下载即用（推荐）

课程验收采用 CLI Release 方案。Windows x64 用户可从 [v1.0.0 Release](https://github.com/RippleOrApple/FR-Harness/releases/tag/v1.0.0) 下载 `FR-Harness-Windows-x64.zip`：

1. 解压整个 ZIP。
2. 双击 `启动 FR-Harness.cmd` 或 `FR-Harness.exe`。
3. 首次运行按中文向导选择供应商、确认模型并隐藏输入 API Key。
4. 在主菜单选择“新建修复任务”。

Release 为单文件 Windows x64 程序，无需安装 Python。ZIP 同时提供 SHA256 校验文件和中文快速开始说明。

无需配置即可先做离线检查：

```powershell
.\FR-Harness.exe demo
```

预期看到四项 `PASS`：危险操作审批、失败反馈纠错、一次性文件审批和任务级 pytest 权限。该演示使用 `MockLLM` 和确定性反馈，不读取 API Key，也不访问网络。

## 交互式 CLI

直接启动 `FR-Harness.exe`、运行 `fr-harness` 或执行 `fr-harness run`，都会进入持续运行的中文主菜单：

```text
1. 新建修复任务
2. 查看历史任务
3. 配置与自检
4. 退出
```

新建任务时：

- 工作区直接回车会使用当前目录，也可以输入另一个现存目录。
- 修复目标采用单行输入，开始前会再次确认。
- 每个任务只询问一次是否允许运行 pytest；授权不会跨任务复用。
- 覆盖已有文件仍逐次审批，并可先查看 unified diff。
- pytest 默认显示摘要，失败时可以展开完整输出。
- 网络错误、限流和服务端临时错误会暂停任务，可从历史任务恢复。
- 任务结束后回到主菜单，不需要重新启动程序。

Windows EXE 的配置、SQLite 数据库和日志默认保存在当前用户的 `LocalAppData/FR-Harness`。API Key 保存到 Windows Credential Manager，不写入 `.env`。

## 从源码运行

Windows 用户推荐直接双击仓库根目录的 `启动 FR-Harness.cmd`。脚本会检测 Python 3.12 或更高版本；如果没有合适的 Python，会尝试通过 `winget` 完成用户级安装。脚本还会自动创建虚拟环境、安装 FR-Harness 及测试依赖，然后打开位于项目根目录的专用 PowerShell。

专用 PowerShell 会默认启动交互菜单。退出菜单后终端仍然保留，可以直接运行全部源码 CLI 命令，例如：

```powershell
fr-harness demo
fr-harness doctor
fr-harness --version
```

脚本只在这个专用 PowerShell 会话中把 `.venv\Scripts` 加入 `PATH`，不会永久修改 PATH，也不会影响其他项目。项目移动到其他目录后仍可通过同一个启动脚本运行。

在普通且没有激活虚拟环境的 PowerShell 中，可以使用明确的可执行文件路径：

```powershell
.\.venv\Scripts\fr-harness.exe demo
```

也可以手动准备源码环境，需要 Python 3.12 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m fr_harness.cli
```

源码模式默认把配置和数据库放在当前仓库目录；可通过 `FR_DATA_DIR` 指向其他数据目录。

首次配置或重新配置：

```powershell
.\.venv\Scripts\python.exe -m fr_harness.cli setup --no-start
.\.venv\Scripts\python.exe -m fr_harness.cli doctor
```

`setup` 会选择模型供应商、确认 Base URL 和模型名、把非敏感配置写入 `.env`、把 API Key 存入 system keyring、初始化数据库并运行 `doctor`。如果直接进入交互模式且配置缺失，程序会自动进入该向导，完成后继续启动菜单。

## 模型供应商

项目调用 OpenAI 兼容 Chat Completions 接口，不限定只能使用 OpenAI。内置预设如下，实际可用模型名以供应商账户为准：

| 供应商 | 默认 Base URL | 默认模型 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com` | `deepseek-v4-flash` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4.1-mini` |
| Kimi / Moonshot | `https://api.moonshot.ai/v1` | `kimi-k3` |
| Qwen / 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |
| 自定义 | 用户输入 | 用户输入 |

真实模型必须能返回符合 `Action` 模型的 JSON，例如：

```json
{"kind":"read_file","path":"README.md"}
```

`doctor` 会检查 `.env`、URL 格式、模型名、凭据来源、HTTP 请求和 Action JSON。HTTP 401 通常表示 Key 无效，402 通常表示余额问题，404/422 通常表示 URL 或模型名不匹配，429 表示请求受限。

## CLI 命令

```text
fr-harness                         启动交互式菜单
fr-harness run                     启动交互式菜单
fr-harness demo                    运行离线机制演示
fr-harness --version               显示版本
fr-harness setup [--no-start]      交互配置
fr-harness doctor                  配置与模型自检
fr-harness serve                   启动可选本地 WebUI
fr-harness init [--database PATH]  初始化数据库
fr-harness test                    运行源码测试套件
fr-harness credential set          保存凭据
fr-harness credential status       查看凭据状态
fr-harness credential update       更新凭据
fr-harness credential clear        清除凭据
```

`test` 与 Agent 的 pytest 工具均使用固定参数数组和 `shell=False`，不接受模型提供的任意命令。pytest 禁用缓存插件，不会在目标项目创建 `.pytest_cache`。

## 空工作区创建

FR-Harness 既可以修复已有 Python 项目，也可以在空工作区中创建小型项目。空目录会被明确标记为 greenfield workspace，Agent 会先根据目标创建文件，不再猜测读取不存在的 `README.md` 或 `app.py`。

新建项目的目标应同时说明源码接口和测试要求，例如：

```text
这是一个空工作区。创建 fibonacci.py，实现 fibonacci(n)；同时创建源码和 pytest 测试文件 test_fibonacci.py，覆盖正常值和负数输入；最后运行 pytest，直到测试通过。
```

当工作区还没有 `test_*.py` 或 `*_test.py` 时，源码写入后允许继续创建测试文件；测试文件存在后，控制器才要求下一步运行 pytest。`no tests ran` 会被视为“需要创建测试”，不会被当成源码实现失败。任务仍然必须取得一次 pytest 通过结果才能完成。

## 架构

```text
交互式 CLI / 可选 WebUI
  -> TaskService（任务创建、恢复、进度和审批协调）
  -> Agent（手写反馈控制循环）
  -> LLMClient（MockLLM / OpenAICompatibleLLM）
  -> Guardrails（工作区边界与危险动作分类）
  -> ToolDispatcher（UTF-8 文件工具 / 固定 pytest）
  -> Feedback / Memory / Audit
  -> SQLite

凭据来源：环境变量优先 -> system keyring
```

任务可在以下状态间变化：

```text
created -> running -> pending_approval -> running -> succeeded
                  |                    |          `-> paused
                  |                    `-> cancelled
                  `-> failed
```

核心机制包括：

- 结构化动作：读取文件、写入文件、运行 pytest、申请审批和声明完成。
- 工作区路径 `resolve()` 校验，阻断 `..` 和符号链接逃逸。
- SQLite 持久化任务、审计、审批、任务权限和记忆。
- 已有文件覆盖采用一次性审批消费，不能重复执行同一批准动作。
- pytest 失败摘要回灌 LLM，只有最近一次测试通过后才能完成。
- 最大轮次、重复动作、阻断动作和可恢复网络错误停止策略。
- 常见 API Key、Token 和 Secret 在持久化或显示前脱敏。

## 凭据与配置

`.env` 只保存非敏感配置：

```env
FR_LLM_BASE_URL=https://api.deepseek.com
FR_LLM_MODEL=deepseek-v4-flash
```

环境变量优先于 system keyring。`OPENAI_API_KEY` 适合 CI、Docker 或临时覆盖；不要把真实值写入源码、Git 历史、终端 history 或日志。`.env` 是明文文件，不是 Secret Manager。

Windows 使用 Windows Credential Manager，macOS 使用 Keychain，Linux 需要可用的 Secret Service。容器环境应使用平台 Secret 注入；状态命令只显示来源，不回显凭据。

`fr-harness.toml` 保存非秘密 Agent 规则：

```toml
[agent]
max_iterations = 8
memory_limit = 5

[approvals]
existing_file_write = true
run_pytest = true
```

`FR_CONFIG_PATH` 可指定其他 TOML；`FR_MAX_ITERATIONS`、`FR_MEMORY_LIMIT`、`FR_APPROVE_EXISTING_WRITE` 和 `FR_APPROVE_PYTEST` 可覆盖对应配置。工作区越界始终阻断，不能通过配置关闭。

## 安全

- Agent 只能访问任务绑定的工作区；容器应使用最小范围读写挂载。
- 覆盖已有文件默认逐次审批；CLI 中 pytest 权限仅对当前任务有效。
- pytest 会执行目标项目的 Python 代码，只应授权可信项目。当前版本没有进程沙箱。
- 固定测试命令禁用 `.pytest_cache`，并使用 `shell=False`。
- 审计、记忆、目标和审批内容会脱敏，但脱敏不能替代最小权限与提交前扫描。
- WebUI 没有登录鉴权，只应监听 `127.0.0.1`，不应直接暴露到不可信网络。

## WebUI（可选）

WebUI 作为本地辅助入口保留，不是本次 Release 的主要交付方式：

```powershell
fr-harness serve --host 127.0.0.1 --port 8000
```

浏览器访问 `http://127.0.0.1:8000/`。页面提供新建任务、任务详情和待审批操作；审批页默认展示易懂的操作摘要，并把原始 JSON 收进技术详情。

## 测试与 CI

源码全量测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -v -p no:cacheprovider
```

兼容课程要求的命令仍可使用：`python -m pytest -v`。

MockLLM 演示：

```powershell
.\.venv\Scripts\python.exe -m fr_harness.cli demo
```

`.github/workflows/ci.yml` 在 push 和 PR 上运行单元测试、离线演示、Docker 构建与冷启动；main 通过后发布 GHCR 镜像。`.github/workflows/release.yml` 在 `v*` 标签上使用 Windows runner：运行测试、构建单文件 EXE、验证版本、离线演示与内置 pytest，再上传 ZIP 和 SHA256 到 GitHub Release。

## Docker

源码构建：

```bash
docker build -t fr-harness:local .
```

公共镜像：

```bash
docker pull ghcr.io/rippleorapple/fr-harness:latest
```

运行时应挂载数据目录和目标工作区，并通过平台 Secret 或未提交的 env 文件注入配置。容器 WebUI 中填写容器内工作区路径。不要把 `.env` 烘焙进镜像。

## 项目结构

```text
src/fr_harness/
  agent.py        # Agent 控制循环与停止策略
  app_paths.py    # 源码和冻结程序运行路径
  cli.py          # CLI 命令与交互入口
  console.py      # 中文菜单、审批 diff 与进度显示
  task_service.py # 任务协调和恢复
  config.py       # TOML 规则
  credentials.py  # system keyring 凭据生命周期
  db.py           # SQLite 仓储与迁移
  demo.py         # 可打包的离线演示
  feedback.py     # pytest 反馈解析
  guardrails.py   # 路径与动作治理
  llm.py          # MockLLM / OpenAI 兼容客户端
  memory.py       # 记忆与上下文
  models.py       # Pydantic 领域模型
  security.py     # 脱敏
  tools.py        # 受限工具
  web.py          # 本地 FastAPI WebUI
.github/workflows/ci.yml
.github/workflows/release.yml
fr-harness.spec
Dockerfile
SPEC.md
PLAN.md
SPEC_PROCESS.md
AGENT_LOG.md
REFLECTION.md
```

## 已知限制

- 只支持 Python 项目，客观反馈信号固定为 pytest。
- 单进程执行，没有后台 worker、多任务并发或跨机器调度。
- 没有多 Agent、IDE 插件、用户认证或生产级权限系统。
- 真实模型必须稳定返回结构化 Action JSON。
- SQLite 状态与文件系统副作用不构成跨系统原子事务；一次性消费保证危险动作至多执行一次。
- Windows Release 当前只提供 x64 构建。

## 课程过程文件

`SPEC.md`、`PLAN.md` 和 `SPEC_PROCESS.md` 记录需求、实现计划、规格迭代和冷启动验证；`AGENT_LOG.md` 与 `temp/` 记录真实实施证据。`REFLECTION.md` 只保留学生个人反思的要求和写作检查项，正文必须由学生根据真实经历自行完成。
