# Task 8 目标：持久化审批与恢复执行

## 目标

把危险动作及其审批决定持久化到 SQLite，并实现跨 Database/Agent 实例恢复、批准后至多执行一次、拒绝后取消任务的工作流。

## 范围

- 扩展 `Database` 的审批创建、读取、列表、决定与原子消费接口。
- 修改 `Agent`，危险动作创建真实审批记录，并新增 `resume_after_approval()`。
- 新建 `tests/test_approvals_integration.py`。
- 抽取可复用的凭据脱敏模块，保证审批 JSON 不含明文 key。

## 验收标准

1. 覆盖已有文件在批准前保持不变。
2. SQLite 重连后仍能读取待审批的完整动作。
3. 批准后动作被条件更新为 `consumed` 并只执行一次；重复恢复不会再次执行。
4. 拒绝后动作永不执行，任务状态为 `cancelled`。
5. 审批请求、决定、消费和工具结果均有审计事件。
6. 审批动作序列化不保存明文凭据。
7. 定向与完整测试通过，提交 `feat: persist approval workflow`。

## 非目标

- 不实现 Web 审批路由；由 Task 9 完成。
