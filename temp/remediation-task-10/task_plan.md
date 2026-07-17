# Task Plan: 公共容器镜像

## Goal

把通过验收的源代码变成可匿名获取、可运行、可追溯到 main 提交的 GHCR 交付物。

## Current Phase

Phase 1

## Phases

### Phase 1: Merge Gate

- [ ] 核对最终 PR checks
- [ ] 使用 expected head SHA 合并 PR #1
- [ ] 同步本地 main
- **Status:** pending

### Phase 2: Publish

- [ ] 等待 main unit-test
- [ ] 等待 main docker-build
- [ ] 等待 publish-image
- [ ] 核对 latest 与 SHA tag
- **Status:** pending

### Phase 3: Public Verification

- [ ] 设置 GHCR package Public
- [ ] 使用空 Docker 配置匿名 pull
- [ ] 冷启动并验证 HTTP 200
- [ ] 扫描容器日志测试凭据
- **Status:** pending

### Phase 4: Evidence

- [ ] 更新 README 与 AGENT_LOG
- [ ] 保存 run、package、tag 和验证命令
- [ ] 运行最终回归
- **Status:** pending

## Decisions Made

| Decision | Rationale |
|---|---|
| 只在 main push 发布 | PR 不需要 packages 写权限 |
| 匿名 pull 使用全新空 `DOCKER_CONFIG` | 证明公共可用而非复用本机登录 |
| WebUI 仅做本地容器冷启动 | 当前无登录鉴权，不把服务公开暴露到互联网 |
