# Goal

## Objective

在 GitHub 托管 runner 上验证正式 PR 的最终提交，确保单元测试、机制演示、文档约束和 Docker 冷启动都真实通过，并保存可复查的 Actions 证据。

## Scope

- 将 Task 8/9 证据提交并推送到 PR 分支。
- 等待对应 GitHub Actions 工作流终态。
- 验证 `unit-test` 与 `docker-build` 成功。
- 确认 PR 上的 `publish-image` 按分支条件跳过，而不是失败。
- 若检查失败，读取日志、定位根因、修复并重新验证。

## Acceptance Criteria

- PR 最新 head 的 required jobs 全部成功。
- 工作流 URL 和 job URL 写入过程文件。
- 本地与远程测试结论一致。
- 失败不会被当成通过，跳过原因有明确解释。
