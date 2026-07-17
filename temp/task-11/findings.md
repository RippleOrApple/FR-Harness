# Findings & Decisions

## Requirements

- 脚本必须真实执行核心机制但完全离线。
- 使用 TemporaryDirectory 和 MockLLM。
- 输出固定三行 PASS，退出码 0。

## Research Findings

- `Agent.resume_after_approval()` 在 consumed 后因任务已 running 会幂等返回。
- `Database.list_events()` 可验证反馈从失败变为通过。
- ToolDispatcher 会捕获 pytest 输出，不污染演示 stdout。
- Python 源文件快速改写的 pyc 问题已由 Task 8 回归修复。

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 临时项目只含 app.py/test_app.py | 最小且执行快速 |
| 第二次恢复前手动改成 sentinel | 能直接证明未重复执行批准动作 |
| 源码安全测试禁止 `os.environ`/OpenAICompatibleLLM | 防止未来演示误接真实配置 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| SQLite `with connection` 不会关闭句柄，Windows 临时目录清理失败 | Database 连接工厂与 MemoryStore 直连均在 finally/closing 中显式关闭 |

## Resources

- `PLAN.md` Task 11
- `SPEC.md` §8
- `src/fr_harness/{agent,db,llm,models}.py`

## Visual/Browser Findings

- 本任务无视觉或浏览器工作。
