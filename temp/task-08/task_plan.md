# Task Plan: Task 8 持久化审批与恢复执行

## Goal

交付跨重启、一次性、安全可审计的 SQLite 审批恢复工作流。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 approvals schema 和 Task 7 审批边界
- [x] 定义记录模型、决定和消费语义
- **Status:** complete

### Phase 2: Tests First
- [x] 编写批准前不执行/批准后一次测试
- [x] 编写拒绝和重启恢复测试
- [x] 编写审批凭据脱敏测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Implementation
- [x] 实现 Database 审批仓储
- [x] 实现 Agent 持久化请求与 resume_after_approval
- [x] 抽取统一安全脱敏函数
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 定向测试通过
- [x] 完整测试通过
- [x] 检查一次性消费和审计顺序
- **Status:** complete

### Phase 5: Delivery
- [x] 更新计划、日志、过程文件
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. “原子消费”如何定义？答：`UPDATE ... WHERE decision='approved'`，只有一个调用能把记录改为 consumed。
2. 执行失败时是否退回 approved？答：不退回；外部文件操作无法与 SQLite 事务原子提交，首版选择 at-most-once，避免重复危险副作用。
3. 如何找到任务当前审批？答：按 SQLite `rowid DESC` 读取最新未消费记录。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `ApprovalRecord` 携带反序列化 Action | Web 和 Agent 无需重复解析 JSON |
| pending/approved/rejected/consumed 全部持久化 | 支持恢复和审计判断 |
| 消费成功后才调用受限工具 | 未获批准或重复恢复绝不产生副作用 |
| 统一 `security.redact_secrets` | 避免 memory/db/agent 循环依赖和规则漂移 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 完整回归中反馈修复闭环失败 | 1 | 审计证据定位为同秒同尺寸覆盖导致旧 pyc 命中；新增红灯后推进 Python 源文件整数 mtime |

## Notes

- 过程 Markdown 全部位于 `temp/task-08/`。
