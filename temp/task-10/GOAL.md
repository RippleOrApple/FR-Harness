# Task 10 目标：CLI、安全配置与 Docker 分发

## 目标

实现可初始化数据库、启动 Web 服务、运行固定测试命令的 CLI，并交付不打包敏感/本地状态的 Python 3.12 Docker 镜像配置。

## 范围

- 实现 `python -m fr_harness.cli init|serve|test`。
- 补齐 `Dockerfile`、`.dockerignore`、`.env.example`。
- 新建 `tests/test_cli.py`。
- 实际执行 Docker 构建（若本机 Docker 可用）。

## 验收标准

1. `init` 创建并初始化 SQLite，stdout 不含 key 名称或值。
2. `serve` 只从 `FR_DATABASE_PATH`、`FR_LLM_BASE_URL`、`FR_LLM_MODEL`、`OPENAI_API_KEY` 读取运行配置，不打印配置值。
3. `test` 使用 `[sys.executable, "-m", "pytest", "-v"]` 且 `shell=False`。
4. Docker 基于 `python:3.12-slim`，暴露 8000 并通过 CLI/Uvicorn 启动。
5. `.dockerignore` 排除 `.git`、`.env`、`.venv`、缓存、SQLite 和 `temp`。
6. `.env.example` 只含占位符，不含真实凭据。
7. 定向与完整测试通过，Docker 构建结果如实记录，提交 `feat: add cli and docker distribution`。

## 非目标

- 不实现生产级进程管理、TLS 或容器编排。
