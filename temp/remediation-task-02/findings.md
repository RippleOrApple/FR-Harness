# Findings & Decisions

## Requirements

- 通用要求 §4.2 的十项 SPEC 内容。
- A.5 的领域与机制设计。
- 凭据安全威胁模型必须明确。

## Research Findings

- 旧 SPEC 有架构和机制，但没有五个用户故事与独立 NFR。
- 旧模块表把 `actions`、`audit` 当作模块，后续 Task 5 会与实现同步。
- 精确模型、护栏、记忆接口仍有价值，应保留。

## Technical Decisions

| Decision | Rationale |
|---|---|
| 验收标准映射到现有/计划测试 | “完成”可客观复查 |
| 明确剩余风险 | 不把脱敏或 keyring 宣称为绝对安全 |

