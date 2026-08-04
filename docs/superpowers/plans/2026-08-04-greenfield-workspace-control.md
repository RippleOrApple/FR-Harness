# 空工作区任务控制 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Agent 在空工作区中按“创建源码、创建测试、运行 pytest”的顺序完成新项目任务，同时保持已有项目写入后立即测试的约束。

**Architecture:** `memory.py` 提供受限、稳定的工作区文件清单，并根据测试文件是否存在生成控制器上下文；`Agent` 每轮把绑定工作区传入上下文构建；`ToolDispatcher` 对空工作区的缺失文件返回可行动反馈。所有行为继续通过既有 Action JSON、审批和工具执行。

**Tech Stack:** Python 3.12、Pydantic、pytest、SQLite。

## Global Constraints

- 工作区清单最多 100 个相对文件路径。
- 忽略 `.git`、`.venv`、`__pycache__`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`.coverage` 和 `htmlcov`。
- 不读取清单中文件内容，不跟随目录符号链接，不越过绑定工作区。
- 只有测试文件存在时，最近一次写入后的下一动作才强制为 `run_pytest`。
- pytest 无测试时下一动作必须创建 `test_*.py` 或 `*_test.py`，不能继续改写源码。

---

### Task 1: 受限工作区清单

**Files:**
- Modify: `src/fr_harness/memory.py`
- Modify: `tests/test_memory.py`

**Interfaces:**
- Produces: `workspace_inventory(root: Path, limit: int = 100) -> list[str]`，返回 POSIX 风格相对文件路径。

- [ ] 在 `tests/test_memory.py` 写失败测试：创建源码、测试、缓存目录和 101 个普通文件，断言结果稳定排序、忽略缓存且不超过 100 项。
- [ ] 运行 `python -m pytest tests/test_memory.py -q`，确认因函数缺失而失败。
- [ ] 使用 `os.walk(..., followlinks=False)` 实现 `workspace_inventory`，原地过滤忽略目录并在达到 limit 时返回。
- [ ] 重新运行 `tests/test_memory.py`，确认通过。
- [ ] 提交 `feat: add bounded workspace inventory`。

### Task 2: 测试状态感知上下文

**Files:**
- Modify: `src/fr_harness/memory.py`
- Modify: `src/fr_harness/agent.py`
- Modify: `tests/test_memory.py`
- Modify: `tests/test_agent.py`

**Interfaces:**
- `build_context(goal, memories, feedback, workspace_files=None)` 新增可选清单参数，保持现有调用兼容。
- `Agent.run_once` 每轮调用 `workspace_inventory(task.workspace)` 并传给 `build_context`。

- [ ] 写失败测试：空清单包含 greenfield 指令；无测试且最近写入时要求创建测试；已有 `test_*.py` 时要求 `run_pytest`；`no tests ran` 反馈要求创建测试。
- [ ] 写 Agent 集成测试：模拟动作依次创建 `fibonacci.py`、创建 `test_fibonacci.py`、运行 pytest、complete，并断言第二轮上下文包含创建测试指令。
- [ ] 运行相关测试，确认因缺少清单参数与条件控制而失败。
- [ ] 实现 `_has_pytest_files`、清单系统消息和条件控制消息；删除无条件“写入后必须 pytest”的规则。
- [ ] 在 Agent 中传递实际工作区清单，运行相关测试并确认通过。
- [ ] 提交 `fix: guide greenfield tasks from source to tests`。

### Task 3: 空目录反馈与文档

**Files:**
- Modify: `src/fr_harness/tools.py`
- Modify: `tests/test_tools.py`
- Modify: `README.md`
- Modify: `tests/test_course_documents.py`

**Interfaces:**
- `read_file` 缺失结果在空目录中提示使用 `write_file` 创建目标文件；非空目录保留现有项目诊断提示。

- [ ] 写失败工具测试和 README 契约测试。
- [ ] 运行定向测试，确认缺少空工作区提示和文档而失败。
- [ ] 实现分支反馈并在 README 增加“空工作区创建”示例及测试要求。
- [ ] 运行定向测试与完整 `python -m pytest -q`。
- [ ] 提交 `docs: explain greenfield task workflow`。

### Task 4: 验证并更新 PR

**Files:**
- Verify: `src/fr_harness/memory.py`
- Verify: `src/fr_harness/agent.py`
- Verify: `src/fr_harness/tools.py`
- Verify: `README.md`

- [ ] 使用当前 `.venv` 运行完整测试。
- [ ] 运行 `fr-harness demo`，确认四项 `PASS`。
- [ ] 检查 `git diff origin/main...HEAD --check` 和新增内容敏感信息。
- [ ] 推送分支，更新 PR #9 描述，并等待 unit-test 与 docker-build 完成。
