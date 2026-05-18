@echo off
setlocal
cd /d "%~dp0.."
call "%~dp000_로컬_환경설정.bat"
if errorlevel 1 pause & exit /b 1
if not exist "tools\simon_resident_agent.py" (
  echo [Simon] tools\simon_resident_agent.py 파일이 없습니다.
  pause
  exit /b 1
)
if not defined SIMON_STT_DEVICE_INDEX set "SIMON_STT_DEVICE_INDEX=1"
if not defined SIMON_STT_SAMPLE_RATE set "SIMON_STT_SAMPLE_RATE=48000"
if not defined SIMON_STT_MODEL set "SIMON_STT_MODEL=small"
if not defined SIMON_STT_LANGUAGE set "SIMON_STT_LANGUAGE=ko"
echo [Simon] Resident를 이 창에서 직접 실행합니다. 에러가 나오면 이 창을 캡처하세요.
echo [Simon] 정상이면 pid 파일이 생기고 창이 유지됩니다. 종료: Ctrl+C
echo.
"%SIMON_RESIDENT_PYTHON%" -X utf8 "tools\simon_resident_agent.py" --device-index %SIMON_STT_DEVICE_INDEX% --sample-rate %SIMON_STT_SAMPLE_RATE% --model %SIMON_STT_MODEL% --language %SIMON_STT_LANGUAGE%
echo.
echo exit code=%ERRORLEVEL%
pause
