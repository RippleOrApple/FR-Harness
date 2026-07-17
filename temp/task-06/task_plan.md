# Task Plan: Task 6 记忆仓储与上下文构建

## Goal

交付 SQLite 任务记忆和安全、顺序确定的 OpenAI Chat 上下文。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 memory_entries schema 与接口约定
- [x] 明确排序、limit、消息顺序和凭据要求
- **Status:** complete

### Phase 2: Tests First
- [x] 编写记忆隔离/排序/limit 测试
- [x] 编写上下文顺序与凭据脱敏测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Implementation
- [x] 实现 MemoryStore
- [x] 实现 build_context 与凭据脱敏
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 定向测试通过
- [x] 完整测试通过
- [x] 检查数据库无明文测试凭据
- **Status:** complete

### Phase 5: Delivery
- [x] 更新 PLAN/AGENT_LOG/过程文件
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. 同秒写入如何稳定排序？答：使用自增 `id DESC`，而非只依赖时间戳。
2. 如何处理意外进入记忆的凭据？答：写入前和构建上下文时双重脱敏。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| relevant 返回 `list[str]` | 遵循 SPEC §5.1 的最小接口 |
| 记忆合并为单条 system 消息 | 固定“安全/记忆/反馈/目标”四类顺序 |
| 使用集中 `_redact_secrets()` | 写入与注入共享同一安全规则 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 首次 RED 为接口导入错误 | 1 | 添加仅抛 `NotImplementedError` 的接口后确认 3 个行为失败 |

## Notes

- 本任务 Markdown 文件全部位于 `temp/task-06/`。
