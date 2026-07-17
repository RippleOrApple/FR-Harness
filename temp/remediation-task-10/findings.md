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

## Merge Evidence

- PR: https://github.com/RippleOrApple/FR-Harness/pull/1
- verified head: `29964b21805876396a8f50154fead0bc5a8c9741`
- merge commit: `2579ff95ec173e340c2e8dd913f8b7ad34aa14fb`
- merged at: 2026-07-17 07:52:42 UTC

## Publish Evidence

- main run: https://github.com/RippleOrApple/FR-Harness/actions/runs/29564500446
- unit-test: https://github.com/RippleOrApple/FR-Harness/actions/runs/29564500446/job/87833986328 — success
- docker-build: https://github.com/RippleOrApple/FR-Harness/actions/runs/29564500446/job/87833986266 — success
- publish-image: https://github.com/RippleOrApple/FR-Harness/actions/runs/29564500446/job/87834083213 — success
- package: https://github.com/RippleOrApple/FR-Harness/pkgs/container/fr-harness
- image: `ghcr.io/rippleorapple/fr-harness:latest`
- SHA tag: `ghcr.io/rippleorapple/fr-harness:sha-2579ff9`

## Anonymous Verification

- 认证目录在 pull 前后文件数均为 0。
- `docker manifest inspect` 在空 `DOCKER_CONFIG` 下成功。
- `docker pull ghcr.io/rippleorapple/fr-harness:latest` 在空 `DOCKER_CONFIG` 下成功。
- manifest digest: `sha256:ba7b5dd3022bcca178e6749468cdbcad43e80b25f636a0103851adfece4c7012`
- 冷启动 HTTP 状态：200。
- 容器日志中的随机测试凭据匹配：0。
- 本机 `gh` token 缺少 `read:packages` 导致包元数据 API 403；这不影响匿名 registry 请求，匿名 manifest 与 pull 是公开性的直接证据。
