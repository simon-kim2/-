# Chat-v2 Control Bar

The control bar is a status-first UI for `/chat_v2`. It does not use Chat NLU and it does not call `/message/sync`.

## Buttons

- `예수금`: reads `/api/status` fields such as `account_summary`, `orderable_cash`, `estimated_asset`, and D+2 values.
- `현황`: reads `/api/status` fields such as `broker_connected`, `connection_status_summary`, `hold`, and `git_hash`.
- `전략`: reads `/api/status` fields such as `mode`, `stage`, `next_stage`, and `position_policy`.
- `자동매매 ON`: posts to `POST /api/control/auto-trade` with `enabled=true`. The server rejects the request unless the status gate is green.
- `자동매매 OFF`: posts to `POST /api/control/auto-trade` with `enabled=false`.
- `음성대화 ON`: enables Chat-v2 TTS only. It does not start browser listening and it does not start Resident.
- `음성대화 OFF`: disables Chat-v2 TTS locally. Resident stop remains an operator/script action.
- `Resident 시작`: posts to `POST /api/control/resident/start`, which asks the server to spawn `scripts/start_simon_resident.bat` after confirmation.
- `POST /api/control/resident/start`: removes a stale pid file, spawns the bat, and waits up to 20s for a live pid. Failure details are written to `data/logs/resident/resident_spawn.log`; `already_running` is based on process liveness, not pid file presence alone.
- `긴급중지`: posts to `POST /api/control/emergency-stop`, which writes an `emergency_stop` IPC command with `hold=true` and `order_execution_enabled=false`.

## Auto-Trade ON Gate

`POST /api/control/auto-trade {"enabled": true}` returns `409` until these are satisfied:

- `read_only_mode=false`
- `hold=false`
- `order_execution_enabled=true`
- `broker_submit_allowed=true`
- `broker_connected=true`
- `executed_order_count=0`
- `status_degraded=false`

## Voice UX

`음성대화 ON` means TTS only. `/chat_v2` does not fake always-listening in the browser without a user gesture. The browser mic button remains a manual fallback.

Resident always-listening is a separate process started by `Resident 시작` or by running `scripts/start_simon_resident.bat /restart`. The target voice path is:

`simon_resident_agent` wake word -> `POST /api/chat/send` -> `GET /api/chat/messages` -> Resident `_speak_text`.
