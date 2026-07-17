# Findings & Decisions

## Requirements

- 危险动作批准前不执行，批准后只执行一次。
- 拒绝使任务取消。
- 待审批在 SQLite 重启后仍存在。
- 决定与消费必须可审计且不泄露凭据。

## Research Findings

- 现有 approvals 表已有 id、task_id、action_json、decision、created_at，足够表达状态机。
- SQLite 隐式 `rowid` 可在同秒创建多条记录时稳定选择最新记录。
- Task 7 的 action 事件已脱敏，但审批动作仍需独立防御直接仓储调用。
- 危险工具本身仍通过 ToolDispatcher 的固定能力边界执行。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 决定接口仅接受 approved/rejected | pending 只能创建产生，consumed 只能执行路径产生 |
| 重复决定抛 ValueError | 防止用户决定被静默覆盖 |
| consume 返回 bool | 并发/重复恢复可安全判断自己是否取得执行权 |
| rejected 记录保留 | 作为不可恢复的审计证据 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 第二次 pytest 仍执行覆盖前的同尺寸 Python 代码 | 检查 SQLite 审计输出确认旧返回值；为 `.py` 覆盖确保整数 mtime 前进，避免 pyc 缓存误命中 |

## Resources

- `PLAN.md` Task 8
- `SPEC.md` §6.3
- `src/fr_harness/db.py`
- `src/fr_harness/agent.py`
- `src/fr_harness/security.py`

## Visual/Browser Findings

- 本任务无视觉或浏览器工作。
