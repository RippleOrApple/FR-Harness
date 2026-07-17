# Findings & Decisions

## Requirements

- 先规格合规，再代码质量。
- Critical/Major 必须修复或给出可验证的驳回理由。
- 评审结果需进入 temp 和 AGENT_LOG。

## Research Findings

- OpenCode 1.17.18 可用，模型 `nju/deepseek-v4-flash`。
- GitHub CLI 已登录 `RippleOrApple`，仓库公开，token 有 repo/workflow。
- 当前分支尚未 push，无 PR。

## Technical Decisions

| Decision | Rationale |
|---|---|
| review 不授权写文件 | 保持评审者独立，只由主 Agent 验证修改 |
| PR 评论发布摘要 | 形成远程可复查证据 |

## Review Findings

- 规格 reviewer 指出线上部署/反思/历史流程缺口；只修复当前可修的真实 diff 与偏差标注。
- 代码 reviewer 无 Critical；接受配置错误分类、动作指纹和 approve 测试。
- WAL/连接池与单任务范围不匹配，保留短连接设计。
