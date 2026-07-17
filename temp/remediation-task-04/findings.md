# Findings & Decisions

## Requirements

- 配置是 Harness 六维之一，必须有可运行最低实现。
- 声明式规则必须由代码消费，不只是一份内容文件。

## Research Findings

- `config.py` 和 `actions.py` 当前为空。
- Action 已唯一实现在 `models.py`，因此删除 `actions.py` 最清晰。
- Agent 已有显式 `max_iterations`，需保留覆盖能力。
- `create_app` 是 CLI 到 Agent 的配置注入点。

## Technical Decisions

| Decision | Rationale |
|---|---|
| `HarnessConfig(agent, approvals)` | 职责和 TOML 分区一致 |
| 允许四个 FR_ 覆盖项 | 容器可调规则但不混入秘密 |

