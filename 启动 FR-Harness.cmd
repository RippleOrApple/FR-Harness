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

if exist ".env" (
    netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
    if not errorlevel 1 (
        echo Port 8000 is already in use. Opening the existing WebUI page...
        rundll32 url.dll,FileProtocolHandler http://127.0.0.1:8000/
        goto done
    )

    echo Starting FR-Harness WebUI on http://127.0.0.1:8000/
    start "" /min cmd /c "timeout /t 2 >nul & rundll32 url.dll,FileProtocolHandler http://127.0.0.1:8000/"
    ".venv\Scripts\python.exe" -m fr_harness.cli serve --host 127.0.0.1 --port 8000
) else (
    echo No .env found. Starting first-run setup...
    ".venv\Scripts\python.exe" -m fr_harness.cli setup
)

:done
echo.
echo FR-Harness has stopped. Press any key to close this window.
pause >nul
