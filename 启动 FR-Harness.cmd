@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv\Scripts\python.exe
    echo Install dependencies in this folder first:
    echo python -m venv .venv
    echo .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m fr_harness.cli run

:done
echo.
echo FR-Harness has stopped. Press any key to close this window.
pause >nul
