@echo off
setlocal
cd /d "%~dp0.."
call "%~dp000_로컬_환경설정.bat" 2>nul
if not defined STOCK_SERVER_PORT set "STOCK_SERVER_PORT=18080"
set "PIDF=data\logs\resident\resident_agent.pid"
echo === Simon 상태 확인 ===
echo.
echo [1] 서버 /api/status
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%STOCK_SERVER_PORT%/api/status' -TimeoutSec 3; Write-Host $r.Content } catch { Write-Host 'FAIL:' $_.Exception.Message }"
echo.
echo [2] Resident /api/resident/status
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%STOCK_SERVER_PORT%/api/resident/status' -TimeoutSec 3; Write-Host $r.Content } catch { Write-Host 'FAIL:' $_.Exception.Message }"
echo.
echo [3] PID 파일
if exist "%PIDF%" (type "%PIDF%") else (echo 없음: %PIDF%)
echo.
echo [4] resident_spawn.log (마지막 8줄)
if exist "data\logs\resident\resident_spawn.log" (
  powershell -NoProfile -Command "Get-Content 'data\logs\resident\resident_spawn.log' -Tail 8"
) else (
  echo 없음
)
echo.
pause
