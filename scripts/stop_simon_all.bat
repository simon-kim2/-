@echo off
setlocal
cd /d "%~dp0\.."
set PYTHONIOENCODING=utf-8
py -3 -X utf8 -m ops.launcher stop
if errorlevel 1 (
  python -X utf8 -m ops.launcher stop
)
