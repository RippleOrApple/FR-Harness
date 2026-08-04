@echo off
chcp 65001 >nul
setlocal EnableExtensions

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    call :bootstrap
    if errorlevel 1 goto failed
)

if not exist ".venv\Scripts\fr-harness.exe" (
    call :install_project
    if errorlevel 1 goto failed
)

set "FR_HARNESS_SOURCE_DIR=%CD%"
set "FR_HARNESS_SOURCE_SCRIPTS=%CD%\.venv\Scripts"

echo 正在打开 FR-Harness 专用 PowerShell...
start "FR-Harness CLI" powershell.exe -NoExit -NoLogo -Command "$env:Path = $env:FR_HARNESS_SOURCE_SCRIPTS + ';' + $env:Path; Set-Location -LiteralPath $env:FR_HARNESS_SOURCE_DIR; fr-harness run"
if errorlevel 1 goto failed
exit /b 0

:bootstrap
echo 未找到本项目的 Python 虚拟环境，开始自动安装...
call :find_python

if not defined BOOTSTRAP_PYTHON (
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [失败] 未找到 Python 3.12 或更高版本，并且此电脑无法使用 winget。
        echo 请先安装 Python 3.12+，然后重新运行本脚本。
        exit /b 1
    )

    echo 未找到 Python 3.12+，正在通过 winget 安装 Python 3.12...
    winget install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [失败] Python 3.12 自动安装失败，请检查网络或手动安装。
        exit /b 1
    )

    call :find_python
    if not defined BOOTSTRAP_PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "BOOTSTRAP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

if not defined BOOTSTRAP_PYTHON (
    echo [失败] Python 已安装，但当前进程仍无法找到它。请关闭窗口后重新运行本脚本。
    exit /b 1
)

echo 正在创建 .venv 虚拟环境...
"%BOOTSTRAP_PYTHON%" %BOOTSTRAP_ARGS% -m venv .venv
if errorlevel 1 (
    echo [失败] 创建 .venv 失败。
    exit /b 1
)

call :install_project
exit /b %errorlevel%

:install_project
echo 正在安装 FR-Harness 及开发依赖，请稍候...
".venv\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 (
    echo [失败] 依赖安装失败，请检查网络后重新运行本脚本。
    exit /b 1
)
echo FR-Harness 运行环境安装完成。
exit /b 0

:find_python
set "BOOTSTRAP_PYTHON="
set "BOOTSTRAP_ARGS="
py -3.12 -c "import sys; raise SystemExit(sys.version_info[:2].__lt__((3, 12)))" >nul 2>&1
if not errorlevel 1 (
    set "BOOTSTRAP_PYTHON=py"
    set "BOOTSTRAP_ARGS=-3.12"
    exit /b 0
)
py -3 -c "import sys; raise SystemExit(sys.version_info[:2].__lt__((3, 12)))" >nul 2>&1
if not errorlevel 1 (
    set "BOOTSTRAP_PYTHON=py"
    set "BOOTSTRAP_ARGS=-3"
    exit /b 0
)
python -c "import sys; raise SystemExit(sys.version_info[:2].__lt__((3, 12)))" >nul 2>&1
if not errorlevel 1 (
    set "BOOTSTRAP_PYTHON=python"
    exit /b 0
)
exit /b 0

:failed
echo.
echo FR-Harness 启动失败。请根据上面的提示处理后重试。
pause
exit /b 1
