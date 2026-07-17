# Goal

## Objective

同步 README、SPEC、PLAN 与凭据/配置/实际模块，消除实现漂移。

## Scope

- 文档列出 keyring 四命令和首次运行行为。
- 文档说明环境优先、keyring 回退、Docker 环境注入。
- 项目结构加入 credentials/config，移除空模块描述。
- 说明 TOML 只保存非秘密规则。

## Acceptance Criteria

- 文档结构测试红后绿。
- README 原安全章节要求继续通过。
- 全量测试通过。

