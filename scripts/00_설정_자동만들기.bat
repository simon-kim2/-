@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
title Simon 설정 자동 만들기

echo.
echo ========================================
echo   Simon 설정 자동 만들기
echo ========================================
echo   이 창만 끝까지 보세요. local_simon.env 를 만들어 줍니다.
echo.

if not exist "config" mkdir "config"
set "OUT=config\local_simon.env"
set "FOUND_PY="
set "FOUND_IDX=1"

echo [1/3] 컴퓨터에서 Python 찾는 중...
echo.

for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "C:\Python313\python.exe"
  "C:\Python312\python.exe"
  "C:\Python311\python.exe"
) do (
  if exist %%P call :try_python %%P
)

where py >nul 2>&1 && for /f "delims=" %%P in ('py -0p 2^>nul') do (
  if exist "%%P" call :try_python "%%P"
)

where python >nul 2>&1 && for /f "delims=" %%P in ('where python 2^>nul') do (
  call :try_python "%%P"
)

if not defined FOUND_PY (
  echo.
  echo [실패] Whisper 되는 Python 을 못 찾았습니다.
  echo.
  echo 직접 경로를 넣어 주세요. 예:
  echo   C:\Users\본인이름\AppData\Local\Programs\Python\Python312\python.exe
  echo.
  set /p "FOUND_PY=python.exe 전체 경로 붙여넣기: "
  if not exist "!FOUND_PY!" (
    echo 파일이 없습니다: !FOUND_PY!
    pause
    exit /b 1
  )
  call :test_whisper "!FOUND_PY!"
  if errorlevel 1 (
    echo.
    echo 이 Python 에 Whisper 가 없습니다. CMD 에서 실행:
    echo   "!FOUND_PY!" -m pip install openai-whisper sounddevice
    pause
    exit /b 1
  )
)

echo.
echo [2/3] 설정 파일 저장: %OUT%
echo       Resident Python = !FOUND_PY!

(
  echo # Simon 자동 생성 설정 - scripts\00_설정_자동만들기.bat
  echo SIMON_RESIDENT_PYTHON=!FOUND_PY!
  echo SIMON_MAIN_PYTHON=C:\Python311_32\python.exe
  echo STOCK_SERVER_PORT=18080
  echo SIMON_STT_DEVICE_INDEX=!FOUND_IDX!
  echo SIMON_STT_SAMPLE_RATE=48000
  echo SIMON_STT_MODEL=small
  echo SIMON_STT_LANGUAGE=ko
) > "%OUT%"

echo.
echo [3/3] 완료
echo.
echo 다음만 더블클릭 하세요:
echo   1. scripts\01_서버_시작.bat
echo   2. scripts\02_Resident_시작.bat
echo   3. scripts\05_채팅_열기.bat
echo.
echo 문제 있으면: scripts\04_Resident_직접실행_에러보기.bat
echo.
pause
exit /b 0

:try_python
set "CAND=%~1"
if not exist "%CAND%" exit /b 0
if defined FOUND_PY exit /b 0
echo   시험 중: %CAND%
call :test_whisper "%CAND%"
if not errorlevel 1 set "FOUND_PY=%CAND%"
exit /b 0

:test_whisper
"%~1" -c "import whisper" 2>nul
if errorlevel 1 exit /b 1
exit /b 0
