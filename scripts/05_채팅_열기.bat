@echo off
setlocal
call "%~dp000_로컬_환경설정.bat" 2>nul
if not defined STOCK_SERVER_PORT set "STOCK_SERVER_PORT=18080"
start "" "http://127.0.0.1:%STOCK_SERVER_PORT%/chat_v2?session_id=resident_default&tts=1"
