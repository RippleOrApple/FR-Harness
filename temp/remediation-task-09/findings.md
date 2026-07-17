# Findings & Decisions

## Requirements

- CI 必须在 GitHub 托管环境真实运行，不用本地结果冒充。
- Python 与 Docker 两条路径都必须成功。
- 镜像发布只允许 main push，PR 不应获得 packages 写权限。

## Initial Findings

- PR #1 已触发两轮工作流（分支 push 与 pull_request）。
- 首轮 `unit-test` 均为 success，耗时约 22 秒。
- 首轮 `docker-build` 均为 success，耗时约 18–19 秒。
- PR/feature 分支上的 `publish-image` 为 skipped，符合 YAML 条件。

## Technical Decisions

| Decision | Rationale |
|---|---|
| 再推送一次过程证据提交 | 让最终 CI 与完整交付状态绑定 |
| 使用 `gh pr checks` 和 run 元数据核对 | 可同时获得结论与公开 URL |

## Initial Remote Evidence

- Run 29563901366
- unit-test: https://github.com/RippleOrApple/FR-Harness/actions/runs/29563901366/job/87832108464
- docker-build: https://github.com/RippleOrApple/FR-Harness/actions/runs/29563901366/job/87832108459
