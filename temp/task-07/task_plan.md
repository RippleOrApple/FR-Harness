# Task Plan: Task 7 自建 Agent 主循环

## Goal

交付受停止策略约束、可确定性测试的自建 Agent 反馈控制循环。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 Task/Action/Feedback、Database、LLM、护栏、工具和记忆接口
- [x] 明确状态转换与审批边界
- **Status:** complete

### Phase 2: Tests First
- [x] 编写完整反馈修复闭环测试
- [x] 编写危险/阻断/重复/预算/提前完成测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Implementation
- [x] 增加任务状态更新接口
- [x] 实现 run_once
- [x] 实现 run_until_stopped 和停止策略
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 定向测试通过
- [x] 完整测试通过
- [x] 审查审计事件和默认护栏路径
- **Status:** complete

### Phase 5: Delivery
- [x] 更新 PLAN/AGENT_LOG/过程文件
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. Task 7 如何验证反馈闭环而不绕过生产安全？答：构造器允许注入护栏分类器供测试隔离，默认始终使用真实 `classify()`。
2. Task 8 前如何表示待审批？答：仅记录审批请求事件和 pending 状态，不提供恢复；下一任务迁移到 SQLite。
3. 如何判断相同动作？答：比较 Pydantic JSON 模式下的完整动作字典。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 每个 LLM 动作计一轮 | 预算与模型决策次数直接对应 |
| 从审计事件恢复最近动作/反馈 | 避免主循环正确性依赖进程内临时状态 |
| terminal/pending 状态调用 run_once 为幂等读取 | 防止停止后意外再次调用 LLM |
| 异常统一写 `error` 事件并置 failed | 可审计且不会无限循环 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 首次 RED 为 Agent 导入错误 | 1 | 添加只定义构造器和抛 `NotImplementedError` 方法的骨架后确认 6 个行为失败 |

## Notes

- 过程 Markdown 全部位于 `temp/task-07/`。
