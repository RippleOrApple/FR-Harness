# FR-Harness 交互式 CLI 与 Windows Release 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 构建中文交互式 CLI、可恢复任务机制和 Windows x64 GitHub Release，使助教无需安装 Python 即可验收 FR-Harness。

**架构：** `cli.py` 只选择运行模式，`console.py` 负责交互，`task_service.py` 协调既有 Agent 与数据库。冻结 EXE 通过 `app_paths.py` 使用 LocalAppData；源码与测试可用环境变量覆盖。任务级 pytest 权限持久化，文件覆盖继续使用一次性审批。

**技术栈：** Python 3.12+、argparse、SQLite、Pydantic、FastAPI、keyring、difflib、PyInstaller、pytest、GitHub Actions。

## 全局约束

- 所有新增界面文字使用中文。
- 不在代码、文档或测试夹具中写入用户名和本机绝对路径。
- 新增生产行为必须先写失败测试并观察预期失败。
- pytest 固定为 `[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]` 且 `shell=False`。
- API Key 不得进入配置、SQLite、日志、diff、终端或 Git。
- 现有 WebUI 行为保持兼容，`serve` 继续可用。
- 不重写公开 Git 历史。

---

### Task 1：运行路径与数据库迁移

**文件：**
- 新建：`src/fr_harness/app_paths.py`
- 修改：`src/fr_harness/models.py`
- 修改：`src/fr_harness/db.py`
- 新建：`tests/test_app_paths.py`
- 修改：`tests/test_models.py`
- 修改：`tests/test_db.py`

**接口：**
- 产出：`RuntimePaths.from_environment(*, frozen: bool | None = None) -> RuntimePaths`
- 产出：`RuntimePaths.ensure() -> None`
- 产出：`Database.set_pytest_allowed(task_id: UUID, allowed: bool) -> Task`
- 产出：`TaskStatus.PAUSED`、`Task.pytest_allowed: bool`

- [x] 先写失败测试：环境变量覆盖数据目录，冻结模式使用 `LOCALAPPDATA/FR-Harness`，源码模式使用当前目录。
- [x] 运行 `python -m pytest tests/test_app_paths.py -v`，确认因模块缺失失败。
- [x] 实现不可变 `RuntimePaths`，包含 `root`、`env_file`、`config_file`、`database_file`、`log_dir`，并提供幂等目录创建。
- [x] 运行目标测试并确认通过。
- [x] 先写失败测试：旧数据库初始化后自动增加 `pytest_allowed`，任务可切换权限并读取；`paused` 可持久化。
- [x] 运行模型和数据库测试，确认字段和方法缺失导致失败。
- [x] 增加 `TaskStatus.PAUSED`、`Task.pytest_allowed`，在 `Database.initialize()` 中通过 `PRAGMA table_info(tasks)` 幂等迁移旧表。
- [x] 更新任务创建、读取和更新 SQL，并实现 `set_pytest_allowed()`。
- [x] 运行 `python -m pytest tests/test_app_paths.py tests/test_models.py tests/test_db.py -v`。
- [x] 提交 `feat: add runtime paths and task permissions`。

### Task 2：可恢复 Agent 状态与完整测试日志

**文件：**
- 修改：`src/fr_harness/models.py`
- 修改：`src/fr_harness/tools.py`
- 修改：`src/fr_harness/agent.py`
- 修改：`tests/test_tools.py`
- 修改：`tests/test_agent.py`

**接口：**
- 产出：`ToolResult.details: str | None`
- 产出：`Agent.pause(task, reason, error_type=None) -> Task`
- 行为：HTTP 429、HTTP 5xx、`httpx.RequestError` 进入 `paused`；其他 LLM 异常仍失败。

- [x] 先写失败测试：pytest 摘要保持 2,000 字符上限，同时 `ToolResult.details` 保存至多 100 KB 原始双流输出。
- [x] 运行目标测试，确认 `details` 缺失导致失败。
- [x] 实现完整输出组合和 100 KB 截断，不改变固定 pytest 命令。
- [x] 运行工具测试并确认通过。
- [x] 先写失败测试：超时、429 和 503 使任务暂停；非法 JSON 仍使任务失败。
- [x] 运行 Agent 测试，确认当前全部被标记失败。
- [x] 实现可恢复异常分类和 `paused` 审计事件；完整日志持久化前调用 `redact_secrets()`。
- [x] 运行 `python -m pytest tests/test_tools.py tests/test_agent.py -v`。
- [x] 提交 `feat: preserve recoverable task state`。

### Task 3：任务协调服务

**文件：**
- 新建：`src/fr_harness/task_service.py`
- 新建：`tests/test_task_service.py`

**接口：**
- 产出：`TaskService.create_task(goal: str, workspace: Path, allow_pytest: bool) -> Task`
- 产出：`TaskService.run(task_id: UUID, approve: ApprovalHandler, on_events: EventHandler) -> Task`
- 产出：`TaskService.resume(task_id: UUID, approve: ApprovalHandler, on_events: EventHandler) -> Task`
- 产出：`TaskService.list_tasks() -> list[Task]`

- [x] 先写失败测试：创建任务保存 pytest 权限；已授权任务运行 pytest 不产生 pytest 审批，但已有文件覆盖仍产生审批。
- [x] 运行 `python -m pytest tests/test_task_service.py -v`，确认模块缺失失败。
- [x] 实现 TaskService，按任务权限复制配置，仅关闭该任务的 pytest 动作审批。
- [x] 逐轮调用 `Agent.run_once()`，把每轮新增审计事件交给 `on_events`。
- [x] 实现文件审批回调和恢复逻辑，拒绝后保持取消状态。
- [x] 增加测试：等待审批、paused 可恢复；成功、失败、取消不可恢复；已消费写入不重复。
- [x] 运行目标测试并确认通过。
- [x] 提交 `feat: add interactive task service`。

### Task 4：中文交互控制台

**文件：**
- 新建：`src/fr_harness/console.py`
- 新建：`tests/test_console.py`

**接口：**
- 产出：`InteractiveConsole.run() -> int`
- 产出：`render_action_diff(workspace: Path, action: Action, limit: int = 20_000) -> DiffPreview`
- 依赖：TaskService、RuntimePaths、setup/doctor 回调。

- [ ] 先写失败测试：主菜单固定四项，退出返回 0；非法选项后重新显示。
- [ ] 运行 `python -m pytest tests/test_console.py -v`，确认模块缺失失败。
- [ ] 实现可注入 `input_fn`、`output_fn` 的控制台和主菜单循环。
- [ ] 增加失败测试：当前目录默认工作区、非法目录重试、空目标拒绝、任务摘要确认和 pytest 权限确认。
- [ ] 实现新建任务流程，并确保拒绝权限不执行 Agent。
- [ ] 增加失败测试：覆盖审批显示相对路径和行数，可查看 unified diff；拒绝后取消。
- [ ] 实现 `DiffPreview` 和审批菜单，diff 经过脱敏并截断。
- [ ] 增加失败测试：pytest 失败显示摘要，用户可查看完整日志；状态和历史列表使用中文且 UUID 默认隐藏。
- [ ] 实现事件渲染、结果摘要、历史查看和允许状态恢复。
- [ ] 增加 `KeyboardInterrupt` 测试，确保任务暂停并返回主菜单。
- [ ] 运行 `python -m pytest tests/test_console.py tests/test_task_service.py -v`。
- [ ] 提交 `feat: add Chinese interactive console`。

### Task 5：CLI 集成与离线 demo

**文件：**
- 修改：`src/fr_harness/cli.py`
- 修改：`demo/mock_repair_demo.py`
- 修改：`tests/test_cli.py`
- 修改：`tests/test_demo.py`
- 修改：`pyproject.toml`

**接口：**
- 行为：无参数和 `run` 进入主菜单。
- 行为：`demo` 输出四项中文 PASS，不读取配置或凭据。
- 行为：`--version` 输出 `fr-harness 1.0.0`。

- [ ] 先写失败测试：无参数和 `run` 调用控制台；配置缺失先 setup，成功后继续原流程。
- [ ] 运行 CLI 测试，确认 parser 要求子命令导致失败。
- [ ] 重构 `main()`，先解析无需配置的 help/version/demo，再根据 RuntimePaths 加载 env、TOML 和数据库。
- [ ] 新增 `[project.scripts] fr-harness = "fr_harness.cli:main"` 和版本 `1.0.0`。
- [ ] 先写失败测试：demo 输出四项中文 PASS 且离线临时运行。
- [ ] 扩展 demo，增加任务级 pytest 权限机制检查。
- [ ] 冻结环境中的 `test` 返回中文提示并引导使用 `demo`；源码环境保持运行 pytest。
- [ ] 运行 `python -m pytest tests/test_cli.py tests/test_demo.py -v`。
- [ ] 提交 `feat: integrate interactive cli commands`。

### Task 6：PyInstaller 与 Release 工作流

**文件：**
- 新建：`fr-harness.spec`
- 新建：`.github/workflows/release.yml`
- 新建：`release/快速开始.txt`
- 修改：`pyproject.toml`
- 新建：`tests/test_release.py`

**接口：**
- 产出：`dist/fr-harness.exe`
- 产出：`FR-Harness-v1.0.0-windows-x64.zip`、`SHA256SUMS.txt`

- [ ] 先写行为测试：PyInstaller spec 可加载且产物名为 `fr-harness`；release workflow 仅响应 `v*` 标签并在 Windows 运行真实 EXE 冒烟命令。
- [ ] 运行 `python -m pytest tests/test_release.py -v`，确认文件缺失失败。
- [ ] 添加 PyInstaller dev 依赖、spec、快速开始和 release workflow。
- [ ] 工作流运行完整 pytest，构建 EXE，在隔离 `FR_DATA_DIR` 下运行 `--help`、`--version`、`demo` 和本地 HTTP 200 冒烟验证。
- [ ] 工作流生成 SHA-256、ZIP，并使用 `gh release create` 上传附件。
- [ ] 本地运行 `pyinstaller --noconfirm fr-harness.spec`，随后运行 EXE 的 help/version/demo。
- [ ] 运行 `python -m pytest tests/test_release.py tests/test_github_actions.py -v`。
- [ ] 提交 `build: add Windows release pipeline`。

### Task 7：文档、隐私与最终验收

**文件：**
- 修改：`README.md`
- 修改：`SPEC.md`
- 修改：`PLAN.md`
- 修改：`AGENT_LOG.md`
- 修改：`REFLECTION.md`
- 修改：`.gitignore`
- 修改：`temp/2026-07-17-remediation-implementation-plan.md`
- 新建：`temp/cli-release/security-scan.md`
- 修改：`tests/test_course_documents.py`
- 修改：`tests/test_readme_security.py`

**接口：**
- 文档明确方案一、Release URL、EXE 快速开始、LocalAppData、CLI 交互、测试与限制。
- REFLECTION 只保留中文学生自写要求，不代写正文。

- [ ] 先更新文档行为测试：要求 setup/doctor/run/demo、正确 pytest 命令、Release、Windows 数据目录和方案一说明。
- [ ] 运行文档测试，确认旧文档不满足要求。
- [ ] 清理当前树中的本机绝对路径；更新 SPEC 状态、CLI、pytest 命令和风险。
- [ ] 在 PLAN 与 AGENT_LOG 补录 setup、doctor、快捷启动、审批卡片、缓存修复和本轮 CLI Release 过程。
- [ ] README 改为从 GitHub Release 下载 EXE 的首选路径，同时保留源码、Docker 和本地 WebUI说明。
- [ ] `.gitignore` 明确加入 `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`.coverage`、`htmlcov/`、`build/`、`dist/`。
- [ ] REFLECTION 改为中文占位与学生自写检查清单，不生成个人反思正文。
- [ ] 扫描当前树和全部历史，只记录命中类别与文件，不写入秘密内容；历史路径残留作为已知事实，不自动重写。
- [ ] 运行文档与隐私测试并确认通过。
- [ ] 运行完整 `python -m pytest -v -p no:cacheprovider` 和 `python demo/mock_repair_demo.py`。
- [ ] 构建 Docker 并完成本地 HTTP 200 冒烟验证。
- [ ] 在全新临时 clone 安装 `.[dev]`、运行完整测试与 demo。
- [ ] 关闭 PR #5，注明已由主分支和本轮 Release 工作取代。
- [ ] 提交 `docs: prepare cli release delivery`。

### Task 8：发布

**文件：**
- 更新：`temp/cli-release/progress.md`
- 更新：`temp/cli-release/task_plan.md`

- [ ] 检查 `git status` 与完整 diff，只暂存本轮文件。
- [ ] 运行最终全量测试、demo、EXE、Docker、隐私扫描和 `git diff --check`。
- [ ] 推送 `agent/cli-release` 并创建面向 `main` 的 ready-for-review PR。
- [ ] 等待并修复 PR 的 unit-test、docker-build 和 Windows release validation 门禁。
- [ ] 合并通过验证的 PR。
- [ ] 在最终 main 提交创建并推送 `v1.0.0` 标签。
- [ ] 等待 Release workflow 完成，验证 Release 页面、ZIP、EXE 和 SHA-256 附件可访问。
- [ ] 在 README 与 AGENT_LOG 补入最终 Release URL；如需补文档，使用独立小 PR 后再确认 Release 说明。
