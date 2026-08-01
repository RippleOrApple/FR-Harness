@echo off
setlocal
cd /d "%~dp0"
"%~dp0FR-Harness.exe"
if errorlevel 1 pause
