# 进度记录

## 2026-08-01

### 阶段 1：规划与基线

- **状态：** 已完成
- 已完成：
  - 用户逐段批准交互流程、组件边界、错误恢复和 Release 设计。
  - 设计文档提交为 `73eaad5`。
  - 从最新 `origin/main` 的 `4188e79` 建立 `agent/cli-release` 隔离 worktree。
  - 创建 GOAL、任务计划、发现和进度记录。
  - 使用 Python 3.13.14 运行隔离 worktree 基线：105 passed。
- 下一步：
  - 开始运行路径与数据库迁移的 TDD 红绿循环。

### 阶段 2：数据模型与运行路径

- **状态：** 已完成
- RED：`test_app_paths.py` 因 `fr_harness.app_paths` 不存在在收集阶段失败。
- GREEN：新增 `RuntimePaths`；任务增加 `paused` 和 `pytest_allowed`；旧 SQLite 自动迁移。
- 回归：目标测试 10 passed，完整测试 111 passed。
- 文件：`app_paths.py`、`models.py`、`db.py` 及对应测试。

### 阶段 3A：可恢复 Agent 状态与完整测试日志

- **状态：** 已完成
- RED：完整日志字段缺失；超时、429、500、503 均被旧实现标记为失败，共 5 failed。
- GREEN：ToolResult 分离 2,000 字符摘要与 100 KB details；可恢复模型错误进入 paused。
- 回归：目标 6 passed，Agent/Tools 22 passed，完整测试 117 passed。

### 阶段 3B：任务协调服务

- **状态：** 已完成
- RED：`fr_harness.task_service` 模块缺失，测试收集失败。
- GREEN：TaskService 逐轮复用 Agent，持久化 pytest 权限，协调一次性覆盖审批和恢复。
- 回归：目标 5 passed，完整测试 122 passed。

### 阶段 3C：中文交互控制台

- **状态：** 已完成
- RED：`fr_harness.console` 模块缺失，测试收集失败。
- GREEN：主菜单、新任务、工作区校验、pytest 授权、diff 审批、历史恢复和 Ctrl+C 保存完成。
- 修正：首轮仅“任务已成功”文案不符，改为“任务已成功完成”后通过。
- 回归：Console/TaskService 12 passed，完整测试 129 passed。

### 阶段 3D：CLI 入口与离线演示

- **状态：** 已完成
- RED：无参数入口、`run`、`demo` 和默认配置测试共 5 项失败。
- GREEN：无参数启动中文菜单；新增 `run`、`demo`、`--version`；运行路径统一由 RuntimePaths 管理。
- 演示：包内 MockLLM 演示覆盖危险操作审批、失败反馈纠错、一次性审批和任务级 pytest 权限。
- 修正：恢复 `FR_CONFIG_PATH` 显式配置优先级，避免 `serve` 错误启动默认配置。
- 回归：目标测试 18 passed，完整测试 132 passed；`demo` 四项均为 PASS。

### 阶段 4：Windows EXE 与 Release 自动化

- **状态：** 已完成
- RED：Release 定义、构建说明和入口测试 2 failed。
- GREEN：新增 PyInstaller 单文件 spec、Windows tag Release workflow、中文快速开始和双击启动脚本。
- 实际构建：PyInstaller 6.21.0 成功生成 Windows x64 单文件 EXE，大小约 18 MB。
- 首次冒烟：`--version` 通过，演示中两项失败；根因是冻结程序不能用自身执行 `-m pytest`。
- 修正：离线演示改用确定性 ToolDispatcher，真实任务的 pytest 执行路径不变。
- 最终冒烟：EXE 版本为 1.0.0，四项离线演示全部 PASS；Release/Demo 目标测试 4 passed。
- 成品缺陷修复：冻结环境的真实任务改为调用 EXE 内置的受控 pytest 入口；独立样例项目可导入自身模块并得到 `1 passed`。

### 阶段 5A：文档与隐私

- **状态：** 进行中
- README 已整体重写，以 Windows Release CLI 为主要交付，源码、可选 WebUI、Docker 与安全说明保持一致。
- SPEC 与 PLAN 已同步交互菜单、任务恢复、任务级 pytest 权限、固定无缓存命令和 Windows EXE。
- AGENT_LOG 已记录真实设计选择、红绿证据、EXE 缺陷和修复过程；REFLECTION 仅保留学生写作要求。
- 当前受跟踪文件：本机路径 0、秘密候选 0、邮箱文件 0。
- 完整历史：秘密/私钥候选 0；旧路径证据仅记录数量，不在报告中复制具体值，不擅自重写已引用历史。
- 已关闭过期 PR #5，并说明其已被后续合并工作取代；GitHub 回查遇到 TLS 超时，但关闭命令返回成功。

### 阶段 6A：干净安装与 Docker 验收

- **状态：** 已完成
- 全新临时 clone：创建独立虚拟环境，安装 `.[dev]`，136 项测试通过，四项 demo 均为 PASS。
- Docker 首次两次构建均因 Docker Hub OAuth token 网络超时失败，与仓库内容无关。
- 分发检查发现 pytest 原本只在 dev extra 中，普通安装与 Docker 不保证核心测试工具可用。
- TDD 修复：新增运行时依赖契约测试并把 pytest 移入项目 dependencies，目标测试 16 passed。
- 使用本机已有的已验证 FR-Harness 镜像作为离线基础层重建当前源码；镜像冷启动 HTTP 200，pytest 9.1.1 可用，测试凭据日志命中 0。

## 测试结果

| 测试 | 期望 | 实际 | 状态 |
|---|---|---|---|
| 基线完整 pytest | 现有测试全部通过 | 105 passed | 通过 |
| Task 1 目标测试 | 路径与数据库迁移通过 | 10 passed | 通过 |
| Task 1 完整回归 | 不破坏现有行为 | 111 passed | 通过 |
| Task 2 红灯 | 新行为尚未实现 | 5 failed, 1 passed | 符合预期 |
| Task 2 完整回归 | 新旧 Agent 与工具行为通过 | 117 passed | 通过 |
| Task 3 目标测试 | 任务权限、审批、进度和恢复 | 5 passed | 通过 |
| Task 3 完整回归 | 不破坏 WebUI 与既有 Agent | 122 passed | 通过 |
| Task 4 目标测试 | 中文交互与任务服务 | 12 passed | 通过 |
| Task 4 完整回归 | 全部现有行为通过 | 129 passed | 通过 |
| Task 5 目标测试 | CLI、路径和离线演示 | 18 passed | 通过 |
| Task 5 完整回归 | CLI 接入不破坏既有行为 | 132 passed | 通过 |
| 离线演示 | 四项安全与反馈行为通过 | 4 PASS | 通过 |
| Windows EXE 构建 | PyInstaller 单文件构建成功 | 约 18 MB EXE | 通过 |
| Windows EXE 冒烟 | 版本与四项离线演示通过 | 1.0.0、4 PASS | 通过 |
| Windows EXE 真实 pytest | 独立项目可导入源码并运行测试 | 1 passed | 通过 |
| 干净 clone | 安装、全量测试、演示 | 136 passed、4 PASS | 通过 |
| Docker 当前源码 | 构建、HTTP、pytest、日志 | 200、pytest 可用、秘密 0 | 通过 |

## 错误日志

| 时间 | 错误 | 次数 | 处理 |
|---|---|---:|---|
| 2026-08-01 | worktree 的 editable install 指向主工作区旧版本 | 1 | 使用 `PYTHONPATH=src` 验证，最终用干净安装复核 |
| 2026-08-01 | `serve` 忽略 FR_CONFIG_PATH，测试错误进入服务监听 | 1 | 显式配置恢复最高优先级，132 项测试通过 |
| 2026-08-01 | EXE 演示使用自身运行 `-m pytest` | 1 | 改为不启动子进程的确定性反馈模拟，成品四项 PASS |
| 2026-08-01 | EXE 真实任务无法用自身执行 `-m pytest` | 1 | 加入隐藏的固定参数 pytest 入口，并以独立项目验证 |
| 2026-08-01 | Docker Hub token 端点连接超时 | 2 | 使用本机已验证镜像作离线基础层重建，托管 CI 仍执行标准 Dockerfile |
| 2026-08-01 | pytest 只在 dev extra，普通安装缺少核心工具 | 1 | 移入运行时 dependencies 并增加打包契约测试 |

## 重启检查

| 问题 | 回答 |
|---|---|
| 当前阶段 | 阶段 5：文档与隐私收尾 |
| 后续阶段 | 文档、隐私检查、完整验收与发布 |
| 最终目标 | 发布可直接验收的 Windows x64 中文交互式 CLI |
| 关键发现 | 见 `findings.md` |
| 已完成工作 | 见本文件 2026-08-01 记录 |
