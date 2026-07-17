# Findings & Decisions

## Requirements

- CLI 包含 init、serve、test。
- serve 环境配置不记录、不回显。
- Docker 3.12 slim、8000、Uvicorn。
- 构建上下文排除敏感和本地状态。

## Research Findings

- `cli.py`、Dockerfile、`.dockerignore`、`.env.example` 当前均为空。
- `uvicorn` 与 `python-dotenv` 已在运行依赖中。
- `create_app()` 可直接接收 Database 路径和 LLM 实例。
- Windows 测试环境适合通过 `main(argv)` 和 monkeypatch 验证而不启动真实服务。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| init 支持 `--database`，默认仍用 FR_DATABASE_PATH | 便于显式初始化和容器环境复用 |
| serve host/port 为 CLI 非敏感参数 | 不扩大敏感配置来源 |
| `.env.example` 模型值使用通用占位符 | 避免绑定会变化的具体模型推荐 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Docker Desktop Linux Engine 初始未运行 | 后台启动 Docker Desktop 并等待 `docker info` 成功，再执行构建 |

## Resources

- `PLAN.md` Task 10
- `SPEC.md` §7、§9
- `src/fr_harness/web.py`
- `pyproject.toml`

## Visual/Browser Findings

- 本任务无视觉或浏览器工作。
