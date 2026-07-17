# Task 11 目标：MockLLM 确定性机制演示

## 目标

交付一个无网络、无真实 key、每次结果一致的可执行演示，证明危险动作审批、pytest 反馈纠错与批准一次性消费三项核心机制。

## 范围

- 新建 `demo/mock_repair_demo.py`。
- 新建 `tests/test_demo.py`，以子进程执行真实脚本。
- 只使用 TemporaryDirectory、SQLite、临时 pytest 项目和 MockLLM。

## 验收标准

1. 脚本退出码为 0，stderr 为空。
2. stdout 恰好三行：
   - `guardrail approval: PASS`
   - `feedback repair: PASS`
   - `approval one-time use: PASS`
3. 未批准时目标文件不变；批准后才写入。
4. 反馈闭环包含 `passed=False` 后 `passed=True`，最终任务 succeeded。
5. 已 consumed 的审批重复恢复不会再次写入。
6. 源码不读取环境 key、不创建网络客户端。
7. 定向与完整测试通过，提交 `test: add deterministic mechanism demo`。

## 非目标

- 不演示真实模型或外部项目。
