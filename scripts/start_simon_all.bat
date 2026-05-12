@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONIOENCODING=utf-8
if "%STOCK_SHADOW_MODE%"=="" set STOCK_SHADOW_MODE=1
if "%STOCK_IPC_MODE%"=="" set STOCK_IPC_MODE=file
py -3 -X utf8 -m ops.launcher start --target server
if errorlevel 1 (
  python -X utf8 -m ops.launcher start --target server
)
