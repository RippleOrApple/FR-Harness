# Task 5 目标：受限工具与 pytest 反馈解析

## 目标

实现只允许 UTF-8 文件读写与固定命令运行 pytest 的工具分发器，并把 pytest 进程结果解析为可回灌给 Agent 的结构化反馈。

## 范围

- 新建 `src/fr_harness/tools.py` 与 `src/fr_harness/feedback.py` 的实质实现。
- 新建 `tests/test_tools.py` 与 `tests/test_feedback.py`。
- 文件路径必须经过 `resolve_workspace_path()`，不得越出工作区。
- pytest 只能通过 `[sys.executable, "-m", "pytest", "-q"]` 执行，不接受模型提供的 shell 字符串。

## 验收标准

1. `read_file` 返回 UTF-8 内容，`write_file` 写入 UTF-8 内容。
2. 路径逃逸被拒绝，未知或非工具动作被拒绝。
3. `run_pytest` 使用固定命令并在任务工作区运行。
4. `parse_pytest_result()` 仅把退出码 0 视为通过，提取 `FAILED ...` 测试节点，摘要不超过 2,000 字符。
5. 先观察新增测试失败，再实现；Task 5 测试与完整测试全部通过。
6. 更新 `PLAN.md` 与 `AGENT_LOG.md`，提交信息为 `feat: add constrained tools and pytest feedback`。

## 非目标

- 不执行任意 shell 命令。
- 不在本任务中实现 Agent 主循环或持久化审批。
