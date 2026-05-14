@echo off
setlocal
cd /d "%~dp0\.."
call "%~dp0stop_simon_all.bat"
timeout /t 2 /nobreak >nul
call "%~dp0start_simon_all.bat"
