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

## 错误日志

| 时间 | 错误 | 次数 | 处理 |
|---|---|---:|---|
| 2026-08-01 | worktree 的 editable install 指向主工作区旧版本 | 1 | 使用 `PYTHONPATH=src` 验证，最终用干净安装复核 |
| 2026-08-01 | `serve` 忽略 FR_CONFIG_PATH，测试错误进入服务监听 | 1 | 显式配置恢复最高优先级，132 项测试通过 |
| 2026-08-01 | EXE 演示使用自身运行 `-m pytest` | 1 | 改为不启动子进程的确定性反馈模拟，成品四项 PASS |
| 2026-08-01 | EXE 真实任务无法用自身执行 `-m pytest` | 1 | 加入隐藏的固定参数 pytest 入口，并以独立项目验证 |

## 重启检查

| 问题 | 回答 |
|---|---|
| 当前阶段 | 阶段 5：文档与隐私收尾 |
| 后续阶段 | 文档、隐私检查、完整验收与发布 |
| 最终目标 | 发布可直接验收的 Windows x64 中文交互式 CLI |
| 关键发现 | 见 `findings.md` |
| 已完成工作 | 见本文件 2026-08-01 记录 |
