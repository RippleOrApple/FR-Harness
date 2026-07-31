@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 未找到 .venv\Scripts\python.exe
    echo 请先在本目录安装依赖：
    echo python -m venv .venv
    echo .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    pause
    exit /b 1
)

if exist ".env" (
    echo 正在打开 FR-Harness WebUI...
    start "" "http://127.0.0.1:8000/"
    ".venv\Scripts\python.exe" -m fr_harness.cli serve --host 127.0.0.1 --port 8000
) else (
    echo 首次运行未找到 .env，正在启动配置向导...
    ".venv\Scripts\python.exe" -m fr_harness.cli setup
)

echo.
echo FR-Harness 已退出。按任意键关闭窗口。
pause >nul
