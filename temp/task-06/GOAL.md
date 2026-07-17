# Task 6 目标：记忆仓储与上下文构建

## 目标

实现基于 SQLite 的任务记忆仓储，以及顺序稳定、不会保存或注入明文凭据的 Agent 上下文构建器。

## 范围

- 实现 `MemoryStore(Database).add()` 与 `relevant()`。
- 实现 `build_context(goal, memories, feedback)`。
- 新建 `tests/test_memory.py`。
- 复用 Task 2 已创建的 `memory_entries` 表。

## 验收标准

1. 记忆按最新优先返回，`limit=2` 排除更早记录，并隔离不同任务。
2. 上下文顺序为：系统安全约束、相关记忆、最近反馈（若有）、用户目标。
3. 最后一条消息 role 为 `user`，此前消息 role 均为 `system`。
4. API Key 等疑似凭据在写入数据库和上下文构建时被替换为 `[REDACTED]`。
5. 先观察测试失败，再实现；定向与完整测试通过。
6. 更新计划/日志并提交 `feat: add task memory context`。

## 非目标

- 不实现向量检索、跨任务记忆或 Agent 循环。
