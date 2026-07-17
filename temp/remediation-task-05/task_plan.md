# Task Plan: 文档实现对齐

## Goal

让正式使用说明和项目结构准确描述当前实现。

## Current Phase

Complete

## Phases

### Phase 1: Discovery

- [x] 扫描空模块和旧命令描述
- [x] 核对凭据/配置真实行为
- **Status:** complete

### Phase 2: TDD RED

- [x] 添加对齐断言
- [x] 观察两项文档失败
- **Status:** complete

### Phase 3: Documentation

- [x] 更新 README
- [x] 更新 PLAN 结构和说明
- [x] 复核 SPEC
- **Status:** complete

### Phase 4: Verification

- [x] 文档与全量测试
- [x] 准备提交
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| `.env` 保留兼容说明但降级为回退 | 满足风险披露，不冒充安全存储 |
| Docker 只使用环境/平台 Secret | 容器不依赖桌面 keyring |
