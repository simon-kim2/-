@echo off
setlocal
cd /d "%~dp0.."
if exist "config\local_simon.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%a in ("config\local_simon.env") do (
    set "_k=%%a"
    call set "_k=%%_k: =%%"
    if not "%%a"=="" if /i not "%%a"=="#" set "%%a=%%b"
  )
)
if not defined STOCK_SERVER_PORT set "STOCK_SERVER_PORT=18080"
if not defined SIMON_RESIDENT_PYTHON (
  echo [Simon] config\local_simon.env 가 없거나 SIMON_RESIDENT_PYTHON 이 비어 있습니다.
  echo        config\local_simon.env.example 를 복사해 local_simon.env 를 만드세요.
  exit /b 1
)
exit /b 0
