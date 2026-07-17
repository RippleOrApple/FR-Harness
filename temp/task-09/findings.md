# Findings & Decisions

## Requirements

- FastAPI 三页：创建、任务详情、审批。
- 创建和审批 POST 使用 303。
- 审计 JSON 必须转义，页面不得显示 key。
- 工作区必须存在且是目录。

## Research Findings

- `pyproject.toml` 已包含 FastAPI/httpx，无模板引擎或 python-multipart。
- Database 已可列出 pending approvals；Agent 可从批准/拒绝结果恢复。
- `html.escape(..., quote=True)` 可覆盖文本和属性中的特殊字符。
- `urllib.parse.parse_qs` 足够解析本任务的 URL-encoded 表单。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| UUID 路由参数交给 FastAPI 校验 | 非法 UUID 自动得到 422，未知资源再返回 404 |
| detail JSON `ensure_ascii=False` | 中文审计可读，同时再进行 HTML 转义 |
| 只在合法 workspace 后创建任务 | 防止任务绑定无效或文件路径工作区 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 当前 Starlette TestClient 发出 httpx 迁移警告 | 精确过滤该上游类别与消息，不影响其他警告 |

## Resources

- `PLAN.md` Task 9
- `SPEC.md` §7
- FastAPI/Starlette 当前项目依赖
- `src/fr_harness/{agent,db}.py`

## Visual/Browser Findings

- 本任务使用 TestClient 验证 HTML，不需要外部浏览器。
