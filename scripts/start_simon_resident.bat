@echo off
setlocal
REM Simon Resident Agent — 바탕화면/시작프로그램에서 실행
REM 64bit Python(Whisper) 권장. Kiwoom용 main.py는 32bit일 수 있음 → SIMON_MAIN_PYTHON
cd /d "%~dp0.."
if not exist "server.py" (
  echo [Simon] BLOCKED: expected stock_trading app root, but server.py was not found.
  exit /b 1
)

if not defined SIMON_RESIDENT_PYTHON (
  where python >nul 2>&1 && set "SIMON_RESIDENT_PYTHON=python"
)
if not defined SIMON_RESIDENT_PYTHON (
  echo [Simon] SIMON_RESIDENT_PYTHON 미설정. Whisper가 설치된 64bit python.exe 경로를 지정하세요.
  exit /b 1
)

if not defined SIMON_MAIN_PYTHON set "SIMON_MAIN_PYTHON=C:\Python311_32\python.exe"

if not defined STOCK_ENABLE_RESIDENT_STT set "STOCK_ENABLE_RESIDENT_STT=1"
if not defined SIMON_RESIDENT_AUTO_SEND set "SIMON_RESIDENT_AUTO_SEND=1"
if not defined SIMON_STT_AUTO_SEND set "SIMON_STT_AUTO_SEND=1"
if not defined SIMON_STT_REQUIRE_WAKE_WORD set "SIMON_STT_REQUIRE_WAKE_WORD=1"
if not defined SIMON_RESIDENT_DEVICE_INDEX set "SIMON_RESIDENT_DEVICE_INDEX=1"
if not defined SIMON_RESIDENT_SAMPLE_RATE set "SIMON_RESIDENT_SAMPLE_RATE=48000"
if not defined SIMON_STT_DEVICE_INDEX set "SIMON_STT_DEVICE_INDEX=%SIMON_RESIDENT_DEVICE_INDEX%"
if not defined SIMON_STT_SAMPLE_RATE set "SIMON_STT_SAMPLE_RATE=%SIMON_RESIDENT_SAMPLE_RATE%"
if not defined SIMON_STT_MODEL set "SIMON_STT_MODEL=small"
if not defined SIMON_STT_LANGUAGE set "SIMON_STT_LANGUAGE=ko"
if not defined SIMON_VAD_RMS_THRESHOLD set "SIMON_VAD_RMS_THRESHOLD=0.006"
if not defined SIMON_VAD_PEAK_THRESHOLD set "SIMON_VAD_PEAK_THRESHOLD=0.05"
if not defined STOCK_SERVER_PORT set "STOCK_SERVER_PORT=18080"
if not defined SIMON_STATUS_URL set "SIMON_STATUS_URL=http://127.0.0.1:%STOCK_SERVER_PORT%/api/status"
if not defined SIMON_CHAT_URL set "SIMON_CHAT_URL=http://127.0.0.1:%STOCK_SERVER_PORT%/chat_v2?session_id=resident_default^&tts=1"
if not defined SIMON_CHAT_V2_SEND set "SIMON_CHAT_V2_SEND=http://127.0.0.1:%STOCK_SERVER_PORT%/api/chat/send"
if not defined SIMON_RESIDENT_TTS_ENABLED set "SIMON_RESIDENT_TTS_ENABLED=1"

set "SIMON_RESIDENT_RESTART=0"
if /I "%~1"=="/restart" (
  set "SIMON_RESIDENT_RESTART=1"
  shift
)

set "PIDF=data\logs\resident\resident_agent.pid"
if exist "%PIDF%" (
  for /f "usebackq delims=" %%p in ("%PIDF%") do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=%%p; try { $x=Get-Process -Id $p -ErrorAction Stop; if ($x.ProcessName -match 'python') { exit 0 } } catch {}; exit 1"
    if not errorlevel 1 (
      if "%SIMON_RESIDENT_RESTART%"=="1" (
        echo [Simon] Restart requested. Stopping existing resident agent PID=%%p
        powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Stop-Process -Id %%p -Force -ErrorAction Stop } catch { Write-Host $_.Exception.Message }"
        del "%PIDF%" >nul 2>&1
        goto START_RESIDENT
      )
      echo [Simon] Existing resident agent detected. PID=%%p
      powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%STOCK_SERVER_PORT%/api/resident/status' -TimeoutSec 3; Write-Host $r.Content } catch { Write-Host $_.Exception.Message }"
      exit /b 0
    )
  )
  echo [Simon] Removing stale resident pid file.
  del "%PIDF%" >nul 2>&1
)

:START_RESIDENT
echo 문제 나면 먼저: "%SIMON_RESIDENT_PYTHON%" tools\resident_health_check.py ^(RESIDENT_HEALTH_RESULT / FAIL_REASONS 확인^)
echo Starting Simon Resident Agent (minimized window)...
start "SimonResidentAgent" /MIN "%SIMON_RESIDENT_PYTHON%" -X utf8 "tools\simon_resident_agent.py" --device-index %SIMON_STT_DEVICE_INDEX% --sample-rate %SIMON_STT_SAMPLE_RATE% --model %SIMON_STT_MODEL% --language %SIMON_STT_LANGUAGE% --speech-open-rms %SIMON_VAD_RMS_THRESHOLD% --peak-open-threshold %SIMON_VAD_PEAK_THRESHOLD% %*
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(12); do { Start-Sleep -Milliseconds 700; try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%STOCK_SERVER_PORT%/api/resident/status' -TimeoutSec 2; $j=$r.Content|ConvertFrom-Json; if ($j.active -and -not $j.stale) { Write-Host ('[Simon] Resident status active=' + $j.active + ' pid_alive=' + $j.pid_alive + ' stale=' + $j.stale + ' phase=' + $j.phase); exit 0 } } catch {} } while ((Get-Date) -lt $deadline); Write-Host '[Simon] Resident start requested, but active/stale=false not confirmed yet. Run tools\\resident_health_check.py.'; exit 0"
exit /b 0
