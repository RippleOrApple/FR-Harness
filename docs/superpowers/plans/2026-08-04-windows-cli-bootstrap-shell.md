# Windows CLI 一键启动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让源码仓库的 Windows 启动脚本自动准备运行环境，并打开一个能够直接执行全部 `fr-harness` 命令的项目 PowerShell。

**Architecture:** CMD 负责定位仓库、自举 Python 与 `.venv`，随后启动独立 PowerShell。新 PowerShell 只在当前会话中把 `.venv\Scripts` 放到 `PATH` 前端，默认执行 `fr-harness run`，退出菜单后仍保持打开。

**Tech Stack:** Windows CMD、PowerShell、Python 3.12+、setuptools console script、pytest。

## Global Constraints

- 不永久修改用户或系统 `PATH`。
- 不在代码或文档中写入本机绝对路径、用户名、API Key 或 Token。
- 所有仓库路径必须从 `%~dp0` 动态计算。
- CMD 必须保存为 UTF-8、CRLF，并在失败时显示中文原因且保留窗口。
- Python 缺失时只允许通过 `winget` 执行用户级 Python 3.12 安装。

---

### Task 1: 启动脚本自举与专用终端

**Files:**
- Modify: `tests/test_cli.py:350`
- Modify: `启动 FR-Harness.cmd`

**Interfaces:**
- Consumes: `pyproject.toml` 中的 `fr-harness = "fr_harness.cli:main"` console script。
- Produces: 双击即可准备 `.venv` 并新开可直接调用 `fr-harness` 的 PowerShell。

- [ ] **Step 1: 写入失败测试**

将启动脚本测试改为 UTF-8 解码，并增加以下断言：

```python
assert "-m venv .venv" in script
assert '-m pip install -e ".[dev]"' in script
assert "winget install --id Python.Python.3.12" in script
assert 'start "FR-Harness CLI" powershell.exe -NoExit' in script
assert "$env:Path" in script
assert "fr-harness run" in script
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_cli.py::test_windows_quick_start_script_is_relative_and_safe -q`

Expected: FAIL，因为现有脚本没有自动创建环境、安装依赖或打开专用 PowerShell。

- [ ] **Step 3: 实现最小启动流程**

在 `启动 FR-Harness.cmd` 中实现：

```batch
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call :bootstrap
start "FR-Harness CLI" powershell.exe -NoExit -NoLogo -Command ^
  "$env:Path = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:Path; fr-harness run"
```

`:bootstrap` 必须依次探测 `py -3.12`、`py -3` 和 `python` 的版本；没有 3.12+ 时调用：

```batch
winget install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
```

随后执行：

```batch
"%BOOTSTRAP_PYTHON%" %BOOTSTRAP_ARGS% -m venv .venv
".venv\Scripts\python.exe" -m pip install -e ".[dev]"
```

- [ ] **Step 4: 转换并验证 CMD 格式**

将脚本机械转换为 UTF-8 无 BOM、CRLF；重新运行定向测试。

Expected: PASS，并且安全断言仍确认脚本不含绝对路径或凭据。

- [ ] **Step 5: 提交脚本与测试**

```bash
git add tests/test_cli.py "启动 FR-Harness.cmd"
git commit -m "feat: bootstrap source CLI in a dedicated shell"
```

### Task 2: 源码命令文档

**Files:**
- Modify: `tests/test_course_documents.py:98`
- Modify: `README.md:45`

**Interfaces:**
- Consumes: Task 1 的专用 PowerShell 行为。
- Produces: 明确区分 Release EXE、专用源码终端和未激活普通终端的命令说明。

- [ ] **Step 1: 写入失败的 README 测试**

在 `test_documented_modules_and_commands_match_repository` 中增加：

```python
for required in (
    "自动创建虚拟环境",
    "专用 PowerShell",
    "不会永久修改 PATH",
    "fr-harness demo",
):
    assert required in readme
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_course_documents.py::test_documented_modules_and_commands_match_repository -q`

Expected: FAIL，因为 README 尚未解释自动安装、专用终端和临时 PATH。

- [ ] **Step 3: 更新 README 源码运行章节**

写明双击 `启动 FR-Harness.cmd` 会自动检测 Python 3.12+、创建 `.venv`、安装依赖并打开专用 PowerShell；该终端中可直接运行：

```powershell
fr-harness demo
fr-harness doctor
fr-harness --version
```

同时明确临时 PATH 不会修改系统配置，普通未激活 PowerShell 仍可使用 `.\.venv\Scripts\fr-harness.exe`。

- [ ] **Step 4: 运行文档测试与完整测试**

Run: `python -m pytest tests/test_course_documents.py::test_documented_modules_and_commands_match_repository -q`

Expected: PASS。

Run: `python -m pytest -q`

Expected: 全部测试通过。

- [ ] **Step 5: 提交文档与测试**

```bash
git add README.md tests/test_course_documents.py
git commit -m "docs: explain source CLI bootstrap shell"
```

### Task 3: 最终验证与 PR

**Files:**
- Verify: `启动 FR-Harness.cmd`
- Verify: `README.md`
- Verify: `tests/test_cli.py`
- Verify: `tests/test_course_documents.py`

**Interfaces:**
- Consumes: Task 1 和 Task 2 的已提交结果。
- Produces: 可评审的 GitHub Pull Request。

- [ ] **Step 1: 验证命令入口**

Run: `.\.venv\Scripts\fr-harness.exe --version`

Expected: 输出 `FR-Harness 1.0.0`。

Run: `.\.venv\Scripts\fr-harness.exe demo`

Expected: 离线演示输出四项 `PASS`，退出码为 0。

- [ ] **Step 2: 检查差异和秘密**

Run: `git diff origin/main...HEAD --check`

Run: `git grep -n -E "[A-Za-z]:\\\\|sk-[A-Za-z0-9_-]{20,}" origin/main...HEAD`

Expected: 无空白错误，修改内容不含本机路径或凭据。

- [ ] **Step 3: 推送并创建 PR**

```bash
git push -u origin fix/windows-cli-bootstrap-shell
gh pr create --base main --head fix/windows-cli-bootstrap-shell --title "feat: add one-click source CLI shell" --body-file temp/pr-body-cli-bootstrap.md
```

PR 描述必须包含行为摘要、测试证据、PATH 不持久化说明和首次安装需要网络的说明。
