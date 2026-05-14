# Simon P0 operational stabilization report

## Scope

This report records the repository-level P0 stabilization baseline. It is not a
live Kiwoom/KIS certification report and does not claim production trading
readiness.

## Verified in this branch

- Local server starts with the standard library HTTP server.
- `/api/status` returns JSON with `view_model_schema=StatusViewModel.v1`.
- `/chat`, `/dashboard/account`, `/dashboard/market`, `/dashboard/orders`, and
  `/dashboard/wall` return HTTP 200 in the smoke check.
- Default status keeps trading disabled:
  - `executed_order_count=0`
  - `auto_trade_enabled=false`
  - `HOLD=true`
  - `broker_submit_enabled=false`
  - `order_execution_enabled=false`
- Order-like voice/chat commands are candidate-only and require approval.
- Question-like order sentences do not create order candidates.
- "order status" commands route to the orders dashboard instead of being treated
  as a new order.
- Watchdog one-shot mode records degraded/down status and can restart the local
  server when explicitly allowed.
- Runtime reports can be generated with `python3 -m ops.generate_report`.

## Known limits

- Real broker connectivity is not implemented in this scaffold.
- Real STT/hotword capture is represented as status only.
- Price feed defaults to unavailable; dashboards must display that condition
  instead of fabricating prices.
- Runtime-generated files are ignored under `runtime/`.
