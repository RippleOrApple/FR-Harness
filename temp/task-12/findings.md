# Findings & Decisions

## Requirements

- README 安全/使用说明完整且 UTF-8。
- CI 有 unit-test job 和镜像构建。
- 最终测试、演示、Docker 冷启动全部通过。
- 个人反思不由 Agent 代写。

## Research Findings

- README 当前只有一句项目简介；CI 文件为空。
- Docker Desktop Engine 已在 Task 10 启动，基础镜像和依赖层已有缓存。
- 容器启动只构造 OpenAI 兼容客户端，不会在访问首页时调用模型端点。
- Web 首页不会渲染环境配置或 key。
- `.gitignore` 已排除 `.env`、虚拟环境、SQLite 和缓存。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| CI 使用 python:3.12-slim 与 docker:dind | 与运行时版本一致并能构建镜像 |
| README Docker 示例使用 `--env-file .env` 同时紧邻风险警告 | 可操作但不掩盖明文风险 |
| 安全测试检查必备短语和真实 key 形态 | 防止后续文档删掉关键安全说明 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| 暂无 | — |

## Release Evidence

- Full verbose suite: 49 passed.
- Mock demo: exact three required PASS lines.
- Docker build: final image `fr-harness:local` exported successfully.
- Cold start: container state running, HTTP 200, test key absent from logs, container cleaned up.
- Credential-shaped tracked-file scan: clean.

## Resources

- `PLAN.md` Task 12
- `SPEC.md` §7、§9、§10
- `.env.example`、Dockerfile、CLI/Web 实现
- `REFLECTION.md` 学生本人撰写边界

## Visual/Browser Findings

- 冷启动通过 HTTP 状态与容器日志验证，不需要视觉截图。
