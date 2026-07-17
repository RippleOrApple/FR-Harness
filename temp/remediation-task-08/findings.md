# Findings & Decisions

## Requirements

- 先规格合规，再代码质量。
- Critical/Major 必须修复或给出可验证的驳回理由。
- 评审结果需进入 temp 和 AGENT_LOG。

## Research Findings

- OpenCode 1.17.18 可用，模型 `nju/deepseek-v4-flash`。
- GitHub CLI 已登录 `RippleOrApple`，仓库公开，token 有 repo/workflow。
- 分支已推送；正式 PR #1 可访问。
- GitHub 连接器未登录，但本机 `gh` 已认证为 `RippleOrApple`，两条评论通过后备渠道发布成功。

## Technical Decisions

| Decision | Rationale |
|---|---|
| review 不授权写文件 | 保持评审者独立，只由主 Agent 验证修改 |
| PR 评论发布摘要 | 形成远程可复查证据 |
| 保留 GitHub 邮箱隐私保护 | 用账号 noreply 身份重写仅本地历史，不公开学校邮箱 |

## Review Findings

- 规格 reviewer 指出线上部署/反思/历史流程缺口；只修复当前可修的真实 diff 与偏差标注。
- 代码 reviewer 无 Critical；接受配置错误分类、动作指纹和 approve 测试。
- WAL/连接池与单任务范围不匹配，保留短连接设计。

## Remote Evidence

- PR: https://github.com/RippleOrApple/FR-Harness/pull/1
- 规格 review 评论: https://github.com/RippleOrApple/FR-Harness/pull/1#issuecomment-5000277406
- 质量 review 评论: https://github.com/RippleOrApple/FR-Harness/pull/1#issuecomment-5000277654
