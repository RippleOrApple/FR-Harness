# Goal

## Objective

将已通过评审与 CI 的 PR 合并到 `main`，由 GitHub Actions 发布 GHCR 镜像，把 package visibility 设为 Public，并在无登录凭据的环境中匿名拉取和冷启动验证。

## Scope

- 合并 PR #1，保留可审计的 merge 记录。
- 等待 main 的 `unit-test`、`docker-build`、`publish-image` 成功。
- 核对 `latest` 与 commit SHA tag。
- 将 `ghcr.io/rippleorapple/fr-harness` 设置为公共包。
- 使用空 `DOCKER_CONFIG` 匿名 pull。
- 运行公共镜像并验证 HTTP 200 与日志不含测试凭据。
- 把最终 URL/tag/命令写入 README 与过程证据。

## Acceptance Criteria

- PR 状态为 merged，main 指向预期内容。
- main 工作流三个 job 全部成功。
- 未登录 Docker 客户端可以拉取 `ghcr.io/rippleorapple/fr-harness:latest`。
- 公共镜像冷启动后返回 HTTP 200。
- 容器日志不包含注入的测试 key。
