# 发现与决策

## 需求

- 助教允许 CLI 项目通过 GitHub Release 链接交付，不要求公网 WebUI。
- 用户选择纯交互式模式、当前目录默认工作区、单行目标和简洁进度。
- pytest 每个任务授权一次，已有文件每次覆盖单独审批。
- diff 和完整 pytest 日志默认隐藏，用户按需查看。
- 任务结束后返回主菜单；历史允许恢复等待审批和中断任务。
- Release 为 Windows x64 单文件 EXE，数据保存到 LocalAppData。
- 本地 WebUI 保留为 `serve` 可选命令。

## 代码库发现

- `cli.py` 已包含 setup、doctor、serve、test 和 credential，但没有终端任务执行入口。
- `Agent.run_until_stopped()` 会隐藏中间轮次，不适合直接驱动终端进度；协调层应逐次调用 `run_once()`。
- `classify()` 的 pytest 审批只读取静态配置；CLI 可按任务构建 `run_pytest=False` 的配置，而不削弱 WebUI 默认审批。
- `Feedback.summary` 限制为 2,000 字符，当前未单独保留供用户查看的完整 pytest 输出。
- `tasks` 表没有迁移版本和任务权限字段，需要幂等 `ALTER TABLE` 迁移。
- 当前 `serve`、`.env` 和配置路径相对启动目录，冻结 EXE 双击运行时不稳定。
- 当前主分支已有 105 项测试、MockLLM 演示、Docker 冷启动和 GHCR 发布工作流。
- 当前过程计划中仍有本机绝对路径；历史也存在同类路径，但重写历史会破坏 commit hash 证据。

## 技术决策

| 决策 | 理由 |
|---|---|
| `RuntimePaths` 集中管理 env、TOML、SQLite 和日志目录 | 避免每个命令各自决定路径 |
| 冻结 EXE 默认 LocalAppData，源码默认当前目录 | 保持现有源码开发体验并改善 Release 体验 |
| 新增 `TaskStatus.PAUSED` | 区分可恢复中断与不可恢复失败 |
| `Task.pytest_allowed` 持久化 | 任务恢复后无需重复授权 |
| `ToolResult.details` 保存脱敏前的原始测试输出，再由 Agent 脱敏持久化 | LLM 摘要和用户日志分离 |
| 标准库 `difflib.unified_diff` | 无新增运行依赖，输出可测试 |
| PyInstaller 作为 dev 依赖 | 仅构建 Release，不增加普通运行依赖 |
| 默认配置内容嵌入应用并在首次运行生成 | 单文件 EXE 不依赖旁边存在 TOML 文件 |
| `FR_CONFIG_PATH` 保持高于运行目录默认值 | 保留自动化与高级用户显式覆盖能力 |
| 离线演示不调用外部 pytest 进程 | 冻结 EXE 的 `sys.executable` 是自身，无法作为 Python 解释器使用 |
| 冻结工具调用隐藏的 `_pytest` 入口 | 保留固定参数与 `shell=False`，同时让无需 Python 的 EXE 可测试目标项目 |
| pytest 是运行时依赖 | CLI、Docker 和普通 pip 安装都需要执行目标测试，不能只放在 dev extra |

## 资源

- 设计：`temp/2026-08-01-cli-release-design.md`
- 实施计划：`temp/2026-08-01-cli-release-implementation-plan.md`
- 课程规格：`SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`
