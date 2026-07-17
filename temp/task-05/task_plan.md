# Task Plan: Task 5 受限工具与 pytest 反馈解析

## Goal

交付安全、可测试的受限文件/pytest 工具与结构化反馈解析器。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 读取 Task 5、SPEC 与现有模型/护栏接口
- [x] 明确安全边界和验收标准
- [x] 记录发现
- **Status:** complete

### Phase 2: Tests First
- [x] 编写反馈解析与工具分发测试
- [x] 运行并确认因缺少实现而失败
- **Status:** complete

### Phase 3: Implementation
- [x] 实现反馈解析器
- [x] 实现受限工具分发器
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 运行 Task 5 测试
- [x] 运行完整测试
- [x] 检查固定 pytest 命令与路径约束
- **Status:** complete

### Phase 5: Delivery
- [x] 更新 PLAN 与 AGENT_LOG
- [x] 审查差异并提交
- **Status:** complete

## Key Questions

1. pytest 输出如何组合？答：按 stdout、stderr 顺序拼接，空段跳过。
2. 非 pytest 工具失败如何表达？答：参数或安全校验错误直接抛出，合法工具返回 `ToolResult`。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `FAILED` 节点按行正则提取并去重 | 与 pytest `-q` 输出稳定匹配，避免重复摘要 |
| subprocess 使用参数数组且 `shell=False` | 从结构上阻止任意 shell 注入 |
| 不自动创建写入目标的父目录 | 保持工具最小能力，避免隐式扩大文件系统修改 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 首次测试收集失败而非行为失败 | 1 | 添加仅抛 `NotImplementedError` 的接口骨架，再次运行并观察 8 个预期行为红灯 |

## Notes

- 所有本任务新增 Markdown 文件均位于 `temp/task-05/`。
