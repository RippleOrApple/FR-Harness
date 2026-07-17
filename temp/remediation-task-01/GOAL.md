# Goal

## Objective

为 FR-Harness 实现操作系统 keyring 凭据生命周期和安全的首次运行引导。

## Scope

- 新增可注入的 `CredentialStore`。
- 实现 `credential set/status/update/clear`。
- `serve` 按“环境变量 → keyring”解析 API key。
- 交互录入使用隐藏输入；Docker/CI 保留环境变量方式。
- 增加离线测试和 `keyring` 依赖。

## Non-goals

- 不实现云端 Secret Manager。
- 不把 key 写入 TOML、`.env`、SQLite 或日志。
- 测试不访问真实操作系统 keyring。

## Acceptance Criteria

- Fake backend 可验证 set/get/update/clear。
- 状态和错误输出不包含密钥。
- 环境变量优先，缺失时读取 keyring。
- 非交互式缺 key 时返回可操作提示。
- 原有 CLI 测试和完整测试保持通过。

## Constraints

- Python 3.12+。
- TDD：先观察相关测试因功能缺失而失败。
- 新过程 Markdown 只放在本目录。

