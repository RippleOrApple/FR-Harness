# Findings & Decisions

## Requirements

- “构建成功”不等于“公共镜像”；必须验证 package visibility 和匿名拉取。
- 镜像必须来自通过测试的 main。
- 凭据只能运行时注入，不进入镜像层、日志或仓库。

## Initial Findings

- 工作流目标镜像：`ghcr.io/rippleorapple/fr-harness`。
- 目标 tag：`latest` 与 `sha-<commit>`。
- `publish-image` 已正确限制为 main push，并依赖测试与 Docker 冷启动。
- PR #1 的单元测试和 Docker 冷启动已在 GitHub runner 上通过。

## Technical Decisions

| Decision | Rationale |
|---|---|
| 合并时提交 expected head SHA | 防止检查后 PR head 被替换 |
| 公开 GHCR 包后再清空客户端认证 | 把发布成功与匿名可用分开验证 |
| 保留本地服务边界 | 无认证 WebUI 不适合公共互联网部署 |
