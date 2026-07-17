# Task Plan: 安全凭据生命周期

## Goal

以系统 keyring 安全保存 API key，并提供完整 CLI 生命周期和运行时解析。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery

- [x] 阅读 GOAL、现有 CLI、依赖和测试
- [x] 明确环境变量优先与 fake backend 边界
- [x] 记录发现
- **Status:** complete

### Phase 2: TDD RED

- [x] 编写凭据存储和 CLI 行为测试
- [x] 运行测试并确认因功能缺失失败
- **Status:** complete

### Phase 3: GREEN & Refactor

- [x] 实现最小凭据模块和 CLI 接入
- [x] 安装依赖并通过相关测试
- [x] 清理重复和错误边界
- **Status:** complete

### Phase 4: Verification

- [x] 运行 CLI/凭据测试
- [x] 运行完整测试
- [x] 扫描输出中无测试秘密
- **Status:** complete

### Phase 5: Delivery

- [x] 更新过程文件
- [x] 准备职责清晰的 commit
- **Status:** complete

## Key Questions

1. keyring 后端不可用时如何避免泄漏底层异常？使用固定通用错误。
2. Docker 无桌面 keyring 时如何运行？环境变量优先，容器不调用 keyring。

## Decisions Made

| Decision | Rationale |
|---|---|
| 注入 KeyringBackend | 离线确定性测试，不触碰真实凭据 |
| 环境变量优先 | 兼容 CI、Docker 和现有部署 |
| set/update 分离 | 防止 set 意外覆盖已有凭据 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| `ModuleNotFoundError: fr_harness.credentials` | 1 | 测试先建立，加入接口骨架后得到 15 个行为红灯 |
