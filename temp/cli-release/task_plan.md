# 任务计划：交互式 CLI 与 Windows Release

## 目标

实现并发布可由助教下载后直接验收的 Windows x64 中文交互式 FR-Harness CLI。

## 当前阶段

阶段 4：EXE 与发布自动化

## 阶段

### 阶段 1：规划与基线

- [x] 确认用户批准的 CLI 交互与 Release 设计。
- [x] 从最新 `origin/main` 建立隔离 worktree。
- [x] 运行基线测试：105 passed。
- [x] 写入实施计划、发现和进度文件。
- **状态：** 已完成

### 阶段 2：数据模型与运行路径

- [x] 按 TDD 实现应用数据目录解析。
- [x] 按 TDD 实现 paused 状态、pytest 任务权限和数据库迁移。
- **状态：** 已完成

### 阶段 3：任务协调与交互控制台

- [x] 按 TDD 实现可恢复错误、任务协调服务和事件进度。
- [x] 按 TDD 实现主菜单、新任务、历史任务、审批、diff 和测试日志。
- [x] 集成 CLI 无参数入口和 `run` 子命令。
- **状态：** 已完成

### 阶段 4：演示、EXE 与发布

- [x] 扩展离线演示并新增 `demo` 命令。
- [x] 添加 PyInstaller 构建与 Windows Release 工作流。
- [x] 本地构建并冒烟验证 EXE。
- **状态：** 已完成

### 阶段 5：文档与隐私收尾

- [ ] 清理当前版本的绝对路径和个人信息。
- [ ] 更新 SPEC、PLAN、AGENT_LOG、README、REFLECTION 占位说明和 `.gitignore`。
- [ ] 完成当前树与完整历史的敏感信息扫描报告。
- [ ] 关闭过期 PR #5。
- **状态：** 未开始

### 阶段 6：完整验证与交付

- [ ] 全量测试、演示、Docker、EXE 和干净 clone 验收。
- [ ] 提交、推送、创建 PR 并等待 CI。
- [ ] 合入通过门禁的变更，创建 `v1.0.0` Release 并验证附件。
- **状态：** 未开始

## 关键问题

1. PyInstaller 单文件运行时如何定位默认 TOML？答：打包默认文件，首次运行复制到用户数据目录；测试可用环境变量覆盖。
2. CLI 如何跳过重复 pytest 审批？答：任务记录持久化 `pytest_allowed`，CLI 构建该任务专用配置时只关闭 pytest 动作审批。
3. 如何避免 CLI 复制 Agent 主循环？答：TaskService 逐次调用 `Agent.run_once()`，只协调显示与审批。
4. Release 应从哪里创建？答：PR 通过并合入 main 后，由 `v1.0.0` 标签触发 Windows Release workflow。

## 决策

| 决策 | 理由 |
|---|---|
| 使用独立 `console.py` | 让终端渲染与业务状态分离，避免继续扩大 `cli.py` |
| 使用 `task_service.py` | CLI 和 WebUI 复用既有 Agent 与数据库机制 |
| 使用任务字段保存 pytest 权限 | 权限需要跨终端恢复，且不能跨任务复用 |
| 完整日志上限 100 KB | 保留排错能力，同时限制数据库和终端输出规模 |
| Windows EXE 默认使用 LocalAppData | 双击或从任意目录启动时行为稳定 |
| 历史扫描但不自动重写历史 | 重写会改变课程证据中的 commit hash，需要单独授权 |

## 错误记录

| 错误 | 次数 | 处理 |
|---|---:|---|
| worktree 使用主目录的 editable install，直接 `python -m` 命中旧代码 | 1 | 验证时显式设置 `PYTHONPATH=src`，最终在干净环境重新安装 |
| 显式配置路径被运行目录默认配置覆盖 | 1 | 保留 `FR_CONFIG_PATH` 的最高优先级并补回归测试 |
| 冻结 EXE 的离线演示尝试用自身执行 `-m pytest` | 1 | 演示改用内置确定性测试反馈，真实任务工具保持不变 |
