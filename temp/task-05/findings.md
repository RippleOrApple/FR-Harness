# Findings & Decisions

## Requirements

- 仅允许读文件、写文件、运行 pytest。
- 文件操作必须限制在任务工作区。
- pytest 固定使用当前 Python 解释器运行 `-m pytest -q`。
- 仅退出码 0 为通过，失败节点与不超过 2,000 字的摘要写入 `Feedback`。

## Research Findings

- `ActionKind` 已包含三种工具动作以及非工具动作 `request_approval`、`complete`。
- `ToolResult` 已具有 `ok`、`output`、可选 `feedback` 字段。
- `resolve_workspace_path()` 已使用 `Path.resolve()` 并防御 `..` 与符号链接逃逸。
- 护栏将覆盖已有文件和 pytest 分类为需要审批；工具本身仍必须独立维持路径与命令约束。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| `parse_pytest_result` 合并 stdout/stderr 后截断 | 保留两类诊断且严格满足摘要长度 |
| `ToolDispatcher.execute` 对非工具 Action 抛 `ValueError` | 明确拒绝超出白名单的动作类型 |
| 使用 `capture_output=True, text=True, encoding="utf-8", errors="replace"` | 返回确定的文本结果并容忍第三方测试的异常字节 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 首次 RED 因接口缺失产生收集错误 | 先添加无行为的接口骨架，再确认全部测试因 `NotImplementedError` 失败 |

## Resources

- `PLAN.md` Task 5
- `SPEC.md` §5.1、§6.2、§6.4
- `src/fr_harness/models.py`
- `src/fr_harness/guardrails.py`

## Visual/Browser Findings

- 本任务不需要浏览器或视觉检查。
