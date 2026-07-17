# Goal

## Objective

新增 GitHub Actions，自动测试、演示、Docker 冷启动并在 main 发布 GHCR。

## Scope

- push/PR 执行 Python 3.12 测试和 Mock 演示。
- Docker build、启动、HTTP 200、日志秘密检查。
- main 登录 GHCR 并发布 latest/sha。
- Dockerfile 增加 OCI source label。

## Acceptance Criteria

- workflow 结构测试通过。
- 本地全量测试和 Docker build 通过。
- 不在 workflow 硬编码真实凭据。

