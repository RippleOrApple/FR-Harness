# Findings & Decisions

## Requirements

- `MemoryStore(Database)` 将 task_id、category、content 写入现有 SQLite 表。
- `relevant(task_id, limit)` 最新优先且最多 limit 条。
- 上下文使用 OpenAI Chat 格式，最后才放用户目标。
- 不保存或注入凭据。

## Research Findings

- `Database._connect()` 已设置 `sqlite3.Row`，可由同包仓储复用。
- `memory_entries.id` 是自增主键，可提供同一秒内的确定排序。
- `Feedback` 包含 passed、summary、failed_tests，可转换为一条紧凑 system 消息。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| SQL 按 `id DESC LIMIT ?` | 简单且确定地返回最近记录 |
| limit 小于 1 时返回空列表 | 避免无意义或 SQLite 特殊负 limit 行为 |
| 匹配常见 KEY/TOKEN/SECRET 赋值和 `sk-` token | 覆盖课程的 OpenAI key 风险而不记录原值 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 首次 RED 为接口导入错误 | 用最小骨架使测试进入行为断言并观察预期失败 |

## Resources

- `SPEC.md` §5.1、§6.5
- `PLAN.md` Task 6
- `src/fr_harness/db.py`
- `src/fr_harness/models.py`

## Visual/Browser Findings

- 本任务无视觉或浏览器工作。
