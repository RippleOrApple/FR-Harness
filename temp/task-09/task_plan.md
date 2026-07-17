# Task Plan: Task 9 FastAPI 与三页 WebUI

## Goal

交付安全转义、可离线测试的任务/详情/审批 WebUI。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 Web 路由、Agent 恢复和审批仓储接口
- [x] 确定无模板依赖的最小 HTML 方案
- **Status:** complete

### Phase 2: Tests First
- [x] 编写创建、校验、转义和审批 API 测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Implementation
- [x] 实现应用工厂与三页 HTML
- [x] 实现创建和审批 POST 路由
- [x] 实现安全表单解析与异常响应
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 定向测试通过
- [x] 完整测试通过
- [x] 检查 HTML 转义和 key 不可见
- **Status:** complete

### Phase 5: Delivery
- [x] 更新计划、日志和过程文件
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. 是否引入模板引擎？答：不引入；页面很小，集中 HTML helper 更易审查转义。
2. 是否依赖 python-multipart？答：不依赖；首版只收 URL-encoded 表单并用标准库解析。
3. 创建任务是否立即运行？答：是，单进程首版同步运行到 terminal 或 pending_approval。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 所有动态文本先 `html.escape` | 防止审计内容形成脚本或标签注入 |
| POST 成功统一 303 | 避免刷新重复提交 |
| app.state 暴露 database/agent | API 测试和后续 CLI 可复用同一实例 |
| 审批后继续运行到下一个停止点 | 完整体现恢复后的 Agent 工作流 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| pytest warning filter 引用了错误类别模块 | 1 | 检查实际 warning category，改为 `starlette.exceptions.StarletteDeprecationWarning` |

## Notes

- 过程 Markdown 全部位于 `temp/task-09/`。
