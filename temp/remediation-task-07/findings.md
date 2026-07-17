# Findings & Decisions

## Research Findings

- GitHub 仓库 `RippleOrApple/FR-Harness` 为 PUBLIC，默认分支 main。
- 当前无 `.github/workflows`。
- Docker `serve` 在提供 endpoint/model/API env 后可启动，不访问 endpoint 即可返回首页。

## Technical Decisions

| Decision | Rationale |
|---|---|
| `docker/metadata-action` 生成 latest/sha | 标准且可追踪 |
| `GITHUB_TOKEN` 仅 publish job packages:write | 最小权限 |

