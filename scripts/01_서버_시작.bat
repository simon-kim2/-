@echo off
setlocal
cd /d "%~dp0.."
if not exist "server.py" (
  echo [Simon] server.py 없음. stock_trading 루트에서 실행하세요.
  pause
  exit /b 1
)
call "%~dp000_로컬_환경설정.bat"
if errorlevel 1 pause & exit /b 1
echo [Simon] 서버 시작 http://127.0.0.1:%STOCK_SERVER_PORT%
echo [Simon] 브라우저: http://127.0.0.1:%STOCK_SERVER_PORT%/chat_v2?session_id=resident_default^&tts=1
echo [Simon] 이 창을 닫으면 서버가 꺼집니다. Ctrl+C 로 종료.
if defined SIMON_MAIN_PYTHON (
  "%SIMON_MAIN_PYTHON%" -X utf8 server.py
) else (
  py -3 -X utf8 server.py 2>nul || python -X utf8 server.py
)
pause
