# Windows CLI 一键启动设计

## 目标

仓库根目录的 `启动 FR-Harness.cmd` 应成为源码模式下唯一需要双击的入口。首次运行时自动准备 Python 环境和项目依赖；后续运行时直接打开一个位于项目根目录的新 PowerShell，并允许用户在其中直接执行 `fr-harness` 及其所有子命令。

## 启动流程

1. 启动脚本始终先切换到脚本自身所在目录，避免依赖调用者的当前目录。
2. 如果 `.venv\Scripts\python.exe` 不存在，脚本查找 Python 3.12 或更高版本。
3. 如果没有合适的 Python，脚本尝试通过 `winget` 按当前用户范围安装 Python 3.12；无法自动安装时显示中文错误并保留窗口。
4. 脚本创建 `.venv`，并执行可编辑安装 `.[dev]`。这一步会根据 `pyproject.toml` 生成 `.venv\Scripts\fr-harness.exe`。
5. 脚本新开 PowerShell，将项目的 `.venv\Scripts` 临时添加到该终端的 `PATH`，并把工作目录设置为项目根目录。
6. 新终端默认执行 `fr-harness run`。用户退出交互菜单后，PowerShell 保持打开，可继续直接运行 `fr-harness demo`、`fr-harness doctor` 等命令。

## 安全与可移植性

- 不永久修改用户或系统 `PATH`。
- 不把本机绝对路径、用户名、API Key 或其他秘密写入脚本和文档。
- 所有路径从 `%~dp0` 动态计算，项目移动后仍然可用。
- Python 自动安装仅在本机不存在 3.12+ 运行时时发生，并采用用户级安装。
- 安装或启动失败时返回非零退出码、显示明确中文原因并等待用户确认，避免窗口闪退。

## 测试

- 静态测试验证脚本包含相对路径、自举、依赖安装、新终端、临时 `PATH` 和 `fr-harness run`。
- 测试验证 CMD 使用 UTF-8 和 CRLF，不包含本机路径与凭据。
- 完整 pytest 套件验证 CLI、Release、WebUI 和安全行为没有回归。

## 文档

README 的源码运行部分明确说明：双击脚本会自动准备环境并打开专用 PowerShell；裸命令 `fr-harness ...` 只在该专用终端或已经激活虚拟环境的终端中直接可用。
