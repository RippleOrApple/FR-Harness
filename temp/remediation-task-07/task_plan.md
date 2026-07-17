# Task Plan: GitHub Actions 与 GHCR

## Goal

建立可产生真实远程 CI 与镜像发布证据的工作流。

## Current Phase

Complete

## Phases

### Phase 1: Discovery

- [x] 确认公开 GitHub 仓库和默认 main
- [x] 核对 Docker 冷启动参数
- **Status:** complete

### Phase 2: TDD RED

- [x] 写 workflow 结构断言
- [x] 观察三项失败
- **Status:** complete

### Phase 3: Workflow

- [x] 实现 test/docker/publish jobs
- [x] 加 OCI label 和 README
- **Status:** complete

### Phase 4: Local Verification

- [x] 测试和 Docker build/冷启动
- [x] 准备提交
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| PR 不发布镜像 | 避免不可信分支获得 package write |
| main publish 依赖两个验证 job | 未验证镜像不得发布 |
| CI placeholder 不使用 key 形态 | 便于日志泄漏断言且不是凭据 |
