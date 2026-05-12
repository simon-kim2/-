# Simon P0 operations scaffold

This repository contains a minimal, safety-first operations layer for Simon.
It is intentionally conservative: it can start a local dashboard server, expose
status JSON, route voice/chat commands to dashboards, and record alerts, but it
does not submit broker orders.

## Safety invariants

- `executed_order_count` defaults to `0`.
- `auto_trade_enabled` defaults to `false`.
- `HOLD` defaults to `true`.
- `broker_submit_enabled` defaults to `false`.
- Voice/order-like commands create at most an approval-required candidate.
- Question-like order sentences are treated as answer/dashboard requests only.

## Local run

```bash
python3 -X utf8 server.py
```

Open:

- `http://127.0.0.1:8080/chat`
- `http://127.0.0.1:8080/dashboard/account`
- `http://127.0.0.1:8080/dashboard/market`
- `http://127.0.0.1:8080/dashboard/orders`
- `http://127.0.0.1:8080/dashboard/wall`
- `http://127.0.0.1:8080/api/status`

On Windows, use the scripts in `scripts/`:

- `start_simon_all.bat`
- `stop_simon_all.bat`
- `restart_simon_server.bat`
- `watch_simon.bat`
- `check_simon_status.ps1`

## Operational checks

```bash
python3 -m ops.watchdog --once --no-restart
python3 -m ops.generate_report
python3 -m unittest discover -s tests
```

The status payload includes `view_model_schema=StatusViewModel.v1` so each
dashboard can bind to the same operational truth source.
