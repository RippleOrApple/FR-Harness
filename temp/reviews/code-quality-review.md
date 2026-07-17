# OpenCode 代码质量与安全评审

## 设置

- 日期：2026-07-17
- Reviewer：第二个全新 OpenCode CLI `--pure` 会话
- 输入：全部 `src/fr_harness`、全部测试、Dockerfile、pyproject、TOML、GitHub workflow
- 权限：只读附件，不调用工具或修改文件

## OpenCode 原始结论

OpenCode 报告无 Critical，并判定可以进入 PR。

Major：

1. `db.py` 未启用 WAL/连接池，可能在 FastAPI 多线程下遇到 `SQLITE_BUSY`。
2. `cli.py` 把配置文件不存在、TOML 错误和 Pydantic 错误统一显示为 `agent configuration is invalid`。

Minor：

1. 重复动作比较脱敏后的 payload，不同秘密可能脱敏成相同值而被误判重复。
2. Web approve 端点缺直接测试。
3. `REQUEST_APPROVAL` 恢复分支缺测试。
4. `PENDING_APPROVAL` 提前返回缺测试。
5. 空事件列表缺测试。
6. 已 consumed/rejected 再 decide 的分支缺测试。
7. `FR_CONFIG_PATH` 指向不存在文件的行为缺测试。

## 人工判断与处理

| 项目 | 判断 | 处理 |
|---|---|---|
| WAL/连接池 | 不采纳为本轮 Major | SPEC 明确单进程、单任务；SQLite 连接短生命周期、默认 busy timeout，CAS 条件更新仍保证一次消费。连接池会重新引入 Windows 临时目录清理问题。并发 worker 不在首版范围 |
| 配置错误分类 | 采纳 | 新增失败测试；`FileNotFoundError` 改为固定 `configuration file was not found`，不输出路径；其他非法配置保持通用错误 |
| 脱敏后重复误判 | 采纳 | 新增失败测试；对原始结构计算 SHA-256 指纹，只持久化脱敏 payload + 不可逆指纹，不保存秘密 |
| Web approve 测试 | 采纳 | 新增路由测试，验证 303、写入和 consumed |
| 其他 Minor 分支 | 暂不扩展 | 核心生命周期已有集成覆盖；低价值分支覆盖不改变本轮前十项结果 |
| 不存在的配置路径应 fallback | 不采纳 reviewer 的“fallback”措辞 | 显式 `FR_CONFIG_PATH` 配错应快速失败，不能静默回退；只改进错误分类 |

## TDD 与验证

- RED：目标三项为 2 failed、1 passed；通过的 approve 测试证明实现已有行为，只是补覆盖。
- GREEN：目标三项 3 passed。
- 回归：完整测试 91 passed。
- 安全：两个不同 secret 值不再误判重复，审计仍不含任一原值。

## 结论

无未处理 Critical。两个可复现的行为问题已修复；WAL/连接池意见因与已批准单任务架构不匹配而有证据地驳回。代码可以进入 PR。

