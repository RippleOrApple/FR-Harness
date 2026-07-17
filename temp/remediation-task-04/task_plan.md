# Task Plan: 声明式 Agent 配置

## Goal

让使用者通过 TOML/环境规则约束 Agent，同时保持安全默认与兼容接口。

## Current Phase

Complete

## Phases

### Phase 1: Discovery

- [x] 阅读 Agent、guardrails、web、cli
- [x] 明确兼容注入方式
- **Status:** complete

### Phase 2: TDD RED

- [x] 写配置加载和运行时消费测试
- [x] 观察 10 个行为失败
- **Status:** complete

### Phase 3: GREEN

- [x] 实现 Pydantic/TOML 配置
- [x] 注入 Agent/guardrails/web/cli
- [x] 删除空模块
- **Status:** complete

### Phase 4: Verification

- [x] 相关测试和全量测试
- [x] 更新证据并准备提交
- **Status:** complete

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 配置接口导入失败 | 1 | 加接口模型骨架后得到 10 个行为红灯 |
| PowerShell 反引号导致 rg 命令解析失败 | 1 | 改用单引号字面 regex 后扫描成功 |

## Decisions Made

| Decision | Rationale |
|---|---|
| Pydantic 模型 + 标准库 tomllib | 已有依赖，验证清晰 |
| 显式 max/classifier 优先于 config | 保持现有测试和 API 兼容 |
| 越界阻断不可配置 | 核心安全边界不能关闭 |
