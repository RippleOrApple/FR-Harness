# Findings & Decisions

## Requirements

- 安全存储、隐藏录入、状态查看、更新、清除。
- API key 不进入源码、Git、日志、终端输出或明文配置。
- 环境变量可作为来源，但不能替代安全存储实现。

## Research Findings

- 当前 `cli.py` 只读取 `OPENAI_API_KEY`，没有生命周期命令。
- `main(argv)` 可扩展一个仅供依赖注入的 store 参数。
- Docker 已通过环境变量运行；优先级能避免无 keyring backend 的容器报错。
- 现有 `security.py` 负责业务内容脱敏，系统 keyring 应独立成模块。

## Technical Decisions

| Decision | Rationale |
|---|---|
| 固定 service=`fr-harness`、account=`openai-api-key` | 稳定定位同一凭据 |
| 底层异常归一化为 CredentialStoreError | 不把后端细节或秘密带入输出 |
| clear 幂等 | 自动化和用户操作可安全重复 |

## Issues Encountered

| Issue | Resolution |
|---|---|
| 首次测试是模块导入错误 | 加入只抛 `NotImplementedError` 的接口骨架，复跑得到 15 个明确行为失败 |
| 本地环境未安装 keyring | 在 pyproject 声明依赖并重新安装 editable 包 |

## Resources

- `src/fr_harness/cli.py`
- `src/fr_harness/security.py`
- `tests/test_cli.py`
- `temp/2026-07-17-remediation-implementation-plan.md`
