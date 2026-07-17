# Task 9 目标：FastAPI 与三页极简 WebUI

## 目标

实现可创建并执行任务、查看状态/转义审计日志、列出并批准或拒绝危险动作的三页 FastAPI WebUI。

## 范围

- 实现 `create_app(database_path, llm) -> FastAPI`。
- 页面：`GET /`、`GET /tasks/{id}`、`GET /approvals`。
- 操作：`POST /tasks`、`POST /approvals/{id}/approve|reject`。
- 新建 `tests/test_web.py`。

## 验收标准

1. 创建合法任务后以 303 重定向到任务详情；非法工作区返回 400。
2. 任务详情显示状态和经过 HTML 转义的审计 JSON。
3. 审批页只列出 pending 项并显示动作影响。
4. 批准/拒绝均持久化决定、恢复任务并以 303 重定向。
5. 页面不显示 LLM API Key 或敏感审计明文。
6. 定向与完整测试通过，提交 `feat: add task and approval web ui`。

## 非目标

- 不实现身份认证、前端框架、后台队列或实时推送。
