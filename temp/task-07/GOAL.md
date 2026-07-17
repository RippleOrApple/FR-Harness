# Task 7 目标：自建 Agent 主循环

## 目标

实现不依赖现成 Agent 框架的确定性控制循环，串联任务持久化、上下文、LLM、护栏、受限工具、反馈、记忆与停止策略。

## 范围

- 实现 `Agent.run_once(task_id)` 与 `run_until_stopped(task_id)`。
- 为任务增加受控的状态/轮次持久化更新接口。
- 新建 `tests/test_agent.py`，覆盖反馈纠错闭环与所有停止条件。

## 验收标准

1. 每轮按“上下文 → LLM 动作 → 护栏 → 工具 → 审计/记忆/反馈”执行。
2. 默认真实护栏下，阻断动作失败，危险动作进入 `pending_approval` 且不执行。
3. pytest 失败反馈进入下一轮上下文；修复后 pytest 通过，再收到 `complete` 才成功。
4. 未通过 pytest 就声明完成必须失败。
5. 默认最多 8 轮；连续两次完全相同的动作必须失败。
6. LLM/工具异常转为失败状态和审计事件，不让循环失控。
7. 定向与完整测试通过，并提交 `feat: add agent feedback control loop`。

## 非目标

- 本任务不持久化审批动作或实现批准后的恢复；由 Task 8 完成。
