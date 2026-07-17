# Task Plan: OpenCode 双评审与 PR

## Goal

在合并前获得独立规格/质量意见，验证后形成远程 PR 证据。

## Current Phase

Complete

## Phases

### Phase 1: Pre-review Verification

- [x] 全量测试和演示
- [x] 工作树/Git 历史凭据扫描
- **Status:** complete

### Phase 2: Specification Review

- [x] 全新 OpenCode pure 会话
- [x] 保存结论和人工判断
- [x] 修复确认问题
- **Status:** complete

### Phase 3: Quality Review

- [x] 第二个全新 pure 会话
- [x] 保存结论和人工判断
- [x] 修复确认问题
- **Status:** complete

### Phase 4: PR

- [x] 最终验证和 review commit 准备
- [x] push 分支和创建 PR
- [x] 发布两条 review 摘要
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| OpenCode 使用两个全新 `--pure` 会话 | 降低共享上下文偏差 |
| 意见按证据人工验证 | 外部 review 是建议，不是命令 |
| GitHub 连接器未登录时使用已认证 `gh` | 保留相同远程评论结果，不阻塞证据链 |
