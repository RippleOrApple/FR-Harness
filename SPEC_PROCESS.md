# FR-Harness Specification Process

This file will record brainstorming iterations and the required cold-start review by a different agent.

## 冷启动验证（补做）— 2026-07-16

### 验证设置

- 主开发 Agent：Codex App。
- 测试 Agent：OpenCode CLI 1.17.18，模型 `nju/deepseek-v4-flash`，因此为不同类型的 Agent。
- 会话隔离：使用不含仓库代码、日志或历史记忆的临时目录 `FRHarness-cold-start-review`，其中仅复制 `SPEC.md` 与 `PLAN.md`；OpenCode 以全新、`--pure` 会话运行。
- 指令：仅根据两份文档评估未实施的 Task 4 与 Task 6；不写代码、不查看其他文件；发现不确定处必须停止提问。

### OpenCode 的正确理解

- 正确识别了 Task 4 的文件、路径逃逸边界、覆盖写入/pytest 审批策略，以及首个失败测试。
- 正确识别了 Task 6 的依赖、记忆/反馈/目标的上下文顺序，以及 limit 测试意图。

### 暴露的问题与修订

| OpenCode 停止点 | 修订前 | 修订后 |
| --- | --- | --- |
| ActionKind 的精确枚举 | 只在已实现代码中存在，文档未列出 | SPEC §5.1 列出 5 个固定值 |
| GuardDecision 与 Approval 的位置/字段 | 未指定 | SPEC §5.1 指定都在 `guardrails.py`，并定义字段 |
| ApprovalStateMachine 是否依赖数据库 | 未指定 | 明确 Task 4 为纯内存状态机，Task 8 才持久化 |
| 覆盖写与符号链接处理 | 只有高层描述 | 明确以 `Path.resolve()` 和 `exists()` 判定 |
| MemoryStore 构造与表 schema | 未指定 | 明确 `MemoryStore(Database)` 和 5 个表字段 |
| LLM Chat 上下文格式与 role | 只给出顺序 | 明确 OpenAI Chat 格式、固定消息顺序与 role |

### 结论

第一次验证判定文档不足以安全开始 Task 4/6。以上修订完成后，需要再次用全新 OpenCode 会话复验；在复验通过前不继续 Task 4。

## 冷启动复验 — 2026-07-16

- 设置：使用另一个全新 `opencode run --pure` 会话，模型仍为 `nju/deepseek-v4-flash`；使用另一临时目录，目录中同样仅有更新后的 SPEC 与 PLAN 副本。
- 结果：OpenCode 明确回答“可以开始”，没有提出阻塞性问题。
- Task 4 首个测试建议：`resolve_workspace_path(..., "../secret.txt")` 抛出 `ValueError("outside workspace")`，以及 pending 审批的 `can_execute()` 返回 False。
- Task 6 首个测试建议：`build_context("fix bug", [], None)` 的第一条为 system、最后一条为 user 目标；3 条记忆在 `limit=2` 时仅返回最新 2 条。
- 结论：复验通过。文档现已足以继续实施 Task 4；先前 Task 1–3 早于验证开始的偏差已如实保留在本文件与 AGENT_LOG 中。
