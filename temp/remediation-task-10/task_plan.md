# Task Plan: 公共容器镜像

## Goal

把通过验收的源代码变成可匿名获取、可运行、可追溯到 main 提交的 GHCR 交付物。

## Current Phase

Complete

## Phases

### Phase 1: Merge Gate

- [x] 核对最终 PR checks
- [x] 使用 expected head SHA 合并 PR #1
- [x] 从 `origin/main` 建立独立证据分支
- **Status:** complete

### Phase 2: Publish

- [x] 等待 main unit-test
- [x] 等待 main docker-build
- [x] 等待 publish-image
- [x] 核对 latest 与 SHA tag
- **Status:** complete

### Phase 3: Public Verification

- [x] 通过匿名 manifest/pull 证明 GHCR package Public
- [x] 使用空 Docker 配置匿名 pull
- [x] 冷启动并验证 HTTP 200
- [x] 扫描容器日志测试凭据
- **Status:** complete

### Phase 4: Evidence

- [x] 更新 README 与 AGENT_LOG
- [x] 保存 run、package、tag 和验证命令
- [x] 运行最终回归
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| 只在 main push 发布 | PR 不需要 packages 写权限 |
| 匿名 pull 使用全新空 `DOCKER_CONFIG` | 证明公共可用而非复用本机登录 |
| WebUI 仅做本地容器冷启动 | 当前无登录鉴权，不把服务公开暴露到互联网 |
