# Findings & Decisions

## Requirements

- 自建循环，不得使用现成 Agent runner。
- 最大 8 轮、连续相同动作失败、阻断失败、危险动作暂停。
- 只有客观 pytest 通过后才允许 complete 成功。
- 每轮写审计，并把失败反馈加入记忆和下一轮上下文。

## Research Findings

- Database 当前只有创建/读取任务和事件接口，需要一个最小 `update_task()`。
- 事件是有序 JSON，可用于恢复最近 Action 和 Feedback。
- `ToolDispatcher` 对 pytest 返回同时包含 output 和结构化 Feedback。
- `MemoryStore` 已按 task 隔离且最新优先。
- Task 8 才规定 SQLite 审批持久化，本任务不能提前实现其完整行为。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| `Agent` 接受可选 dispatcher/classifier | 真实默认安全，测试可隔离主循环机制 |
| 工具结果/反馈拆成不同审计事件 | 详情页和后续上下文各取所需 |
| complete 读取最近一条反馈的 passed | 防止模型声明覆盖客观失败 |
| request_approval 与 requires_approval 均进入 pending | 结构化显式请求同样遵守暂停语义 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 首次 RED 为接口导入错误 | 添加无行为 Agent 骨架，使测试进入有效失败阶段 |

## Resources

- `SPEC.md` §6.1–§6.5
- `PLAN.md` Task 7
- `src/fr_harness/{db,llm,guardrails,tools,memory,models}.py`

## Visual/Browser Findings

- 本任务无视觉或浏览器工作。
