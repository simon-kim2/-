@echo off
setlocal
cd /d "%~dp0.."
call "%~dp000_로컬_환경설정.bat"
if errorlevel 1 pause & exit /b 1
echo [Simon] Resident 시작 (Whisper 64bit: %SIMON_RESIDENT_PYTHON%)
call "%~dp0start_simon_resident.bat" /restart
echo.
echo [Simon] 확인: scripts\03_상태_확인.bat
pause
