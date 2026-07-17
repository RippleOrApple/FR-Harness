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
