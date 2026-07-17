# Goal

## Objective

实现不含秘密的声明式 Agent 配置，并清理无职责空模块。

## Scope

- TOML 配置迭代上限、记忆条数和两类审批策略。
- 允许受控环境变量覆盖。
- 配置注入 Agent、guardrails、WebUI 和 CLI。
- 删除空 `actions.py`，保留合法空 `__init__.py`。

## Non-goals

- 配置文件不保存 API key。
- 工作区逃逸阻断不可关闭。

## Acceptance Criteria

- 默认值安全，非法值快速失败。
- 环境覆盖 TOML。
- Agent 使用 memory/max 配置。
- 审批策略可声明，越界仍阻断。
- 相关及全量测试通过。

