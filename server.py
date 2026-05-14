from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from simon_ops.alerts import notify
from simon_ops.dashboard_commands import route_voice_command
from simon_ops.state import build_status, ensure_runtime_dir


def json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def html_page(title: str, body: str, auto_refresh: bool = True) -> bytes:
    refresh = """
    <script>
      async function refreshStatus() {
        try {
          const r = await fetch('/api/status', {cache: 'no-store'});
          const data = await r.json();
          document.querySelectorAll('[data-bind="executed_order_count"]').forEach(e => e.textContent = data.core.executed_order_count);
          document.querySelectorAll('[data-bind="auto_trade_enabled"]').forEach(e => e.textContent = data.core.auto_trade_enabled);
          document.querySelectorAll('[data-bind="HOLD"]').forEach(e => e.textContent = data.core.HOLD);
          document.querySelectorAll('[data-bind="price_feed_available"]').forEach(e => e.textContent = data.core.price_feed_available);
          document.querySelectorAll('[data-bind="resident_status"]').forEach(e => e.textContent = data.resident.status);
        } catch (err) {
          const banner = document.getElementById('status-error');
          if (banner) banner.textContent = 'status timeout/down: ' + err;
        }
      }
      setInterval(refreshStatus, 3000);
      window.addEventListener('load', refreshStatus);
    </script>
    """ if auto_refresh else ""
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #0f172a; color: #e5e7eb; }}
    header {{ display: flex; gap: 12px; align-items: center; padding: 16px 24px; background: #111827; border-bottom: 1px solid #374151; }}
    header a {{ color: #93c5fd; text-decoration: none; font-weight: 650; }}
    main {{ padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .card {{ background: #111827; border: 1px solid #374151; border-radius: 14px; padding: 16px; box-shadow: 0 6px 20px rgb(0 0 0 / 25%); }}
    .danger {{ border-color: #ef4444; }}
    .warn {{ border-color: #f59e0b; }}
    .ok {{ border-color: #22c55e; }}
    .label {{ color: #9ca3af; font-size: 13px; }}
    .value {{ font-size: 22px; font-weight: 750; margin-top: 4px; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; background: #111827; border: 1px solid #374151; }}
    th, td {{ text-align: left; border-bottom: 1px solid #374151; padding: 10px; vertical-align: top; }}
    th {{ color: #bfdbfe; width: 280px; }}
    button {{ border: 0; border-radius: 10px; padding: 12px 16px; font-weight: 750; }}
    button:disabled {{ background: #4b5563; color: #d1d5db; cursor: not-allowed; }}
    input {{ width: min(760px, 100%); padding: 12px; border-radius: 10px; border: 1px solid #475569; background: #020617; color: #e5e7eb; }}
    pre {{ white-space: pre-wrap; background: #020617; border: 1px solid #374151; border-radius: 12px; padding: 14px; }}
    .banner {{ margin-bottom: 16px; padding: 12px; border-radius: 10px; background: #7f1d1d; color: #fee2e2; }}
  </style>
</head>
<body>
  <header>
    <strong>Simon Ops P0</strong>
    <a href="/chat">Chat</a>
    <a href="/dashboard/account">Account</a>
    <a href="/dashboard/market">Market</a>
    <a href="/dashboard/orders">Orders</a>
    <a href="/dashboard/wall">Wall</a>
    <a href="/api/status">Status JSON</a>
  </header>
  <main>
    <div id="status-error" class="banner"></div>
    {body}
  </main>
  {refresh}
</body>
</html>"""
    return html.encode("utf-8")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def status_cards(status: dict[str, Any]) -> str:
    core = status["core"]
    resident = status["resident"]
    return f"""
<section class="grid" aria-label="운영 상태 카드">
  <div class="card warn"><div class="label">price_feed_available</div><div class="value" data-bind="price_feed_available">{esc(core["price_feed_available"])}</div></div>
  <div class="card warn"><div class="label">market_data_limited</div><div class="value">{esc(core["market_data_limited"])}</div></div>
  <div class="card danger"><div class="label">executed_order_count</div><div class="value" data-bind="executed_order_count">{esc(core["executed_order_count"])}</div></div>
  <div class="card danger"><div class="label">auto_trade_enabled</div><div class="value" data-bind="auto_trade_enabled">{esc(core["auto_trade_enabled"])}</div></div>
  <div class="card warn"><div class="label">HOLD</div><div class="value" data-bind="HOLD">{esc(core["HOLD"])}</div></div>
  <div class="card warn"><div class="label">Resident</div><div class="value" data-bind="resident_status">{esc(resident["status"])}</div></div>
</section>
"""


def render_chat() -> bytes:
    status = build_status()
    body = f"""
<h1>채팅 / 음성 명령 테스트</h1>
{status_cards(status)}
<p>예: <code>사이먼 현황 보여줘</code>, <code>사이먼 시장 보여줘</code>, <code>사이먼 주문 상태 보여줘</code></p>
<form id="chat-form">
  <input id="chat-input" name="message" value="사이먼 현황 보여줘" autocomplete="off">
  <button type="submit">전송</button>
</form>
<pre id="chat-result">주문/자동매매는 승인 없이 실행되지 않습니다.</pre>
<script>
document.getElementById('chat-form').addEventListener('submit', async (event) => {{
  event.preventDefault();
  const message = document.getElementById('chat-input').value;
  const response = await fetch('/api/chat', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{message}})
  }});
  const data = await response.json();
  document.getElementById('chat-result').textContent = JSON.stringify(data, null, 2);
  if (data.route && data.route.action === 'open_dashboard') {{
    window.open(data.route.target_url, '_blank');
  }}
}});
</script>
"""
    return html_page("Simon Chat", body)


def render_account() -> bytes:
    status = build_status()
    core = status["core"]
    body = f"""
<h1>계좌 현황</h1>
{status_cards(status)}
<table>
  <tr><th>모드</th><td>{esc(core["mode"])}</td></tr>
  <tr><th>계좌번호</th><td>{esc(core["account_number"] or "not_connected")}</td></tr>
  <tr><th>예수금</th><td>{esc(core["cash_balance"] if core["cash_balance_available"] else "unavailable")}</td></tr>
  <tr><th>보유수량</th><td>{esc(json.dumps(core["holdings"], ensure_ascii=False))}</td></tr>
  <tr><th>브로커</th><td>{esc(core.get("broker_vendor", "kis"))} / 프로파일 {esc(core.get("broker_profile", "kis_paper"))} / 연결 {esc(core.get("broker_connected", False))}</td></tr>
  <tr><th>데이터 제한</th><td>market_data_limited={esc(core["market_data_limited"])}</td></tr>
</table>
"""
    return html_page("Simon Account", body)


def render_market() -> bytes:
    status = build_status()
    core = status["core"]
    body = f"""
<h1>시장 대시보드</h1>
{status_cards(status)}
<table>
  <tr><th>현재가 source</th><td>{esc(core["current_price_source"])}</td></tr>
  <tr><th>price_feed_available</th><td>{esc(core["price_feed_available"])}</td></tr>
  <tr><th>stale_price</th><td>{esc(core["stale_price"])}</td></tr>
  <tr><th>market_data_limited</th><td>{esc(core["market_data_limited"])}</td></tr>
  <tr><th>OpenAPI 오류</th><td>{esc(json.dumps(core["openapi_errors"], ensure_ascii=False))}</td></tr>
</table>
"""
    return html_page("Simon Market", body)


def render_orders() -> bytes:
    status = build_status()
    core = status["core"]
    disabled = "disabled" if not core["order_execution_enabled"] else ""
    reasons = ", ".join(core["order_execution_block_reason"])
    body = f"""
<h1>주문 대시보드</h1>
{status_cards(status)}
<table data-testid="orders-detail-table">
  <tr><th>모드: 모의/실전</th><td>{esc(core["mode"])}</td></tr>
  <tr><th>계좌번호</th><td>{esc(core["account_number"] or "not_connected")}</td></tr>
  <tr><th>종목명/코드</th><td>{esc(core["pending_order"] or "pending_order 없음")}</td></tr>
  <tr><th>현재가 source</th><td>{esc(core["current_price_source"])}</td></tr>
  <tr><th>stale_price</th><td>{esc(core["stale_price"])}</td></tr>
  <tr><th>예수금</th><td>{esc(core["cash_balance"] if core["cash_balance_available"] else "unavailable")}</td></tr>
  <tr><th>보유수량</th><td>{esc(json.dumps(core["holdings"], ensure_ascii=False))}</td></tr>
  <tr><th>주문 수량</th><td>not_set</td></tr>
  <tr><th>예상금액</th><td>unavailable</td></tr>
  <tr><th>승인 상태</th><td>{esc(core["approval_status"])}</td></tr>
  <tr><th>ApprovalGuard 상태</th><td>{esc(core["approval_guard_status"])}</td></tr>
  <tr><th>RiskGuard 상태</th><td>{esc(core["risk_guard_status"])}</td></tr>
  <tr><th>TradingExecutionPolicy 결과</th><td>{esc(core["trading_execution_policy"])}</td></tr>
  <tr><th>price_feed_available</th><td>{esc(core["price_feed_available"])}</td></tr>
  <tr><th>order_execution_enabled</th><td>{esc(core["order_execution_enabled"])}</td></tr>
  <tr><th>order_execution_block_reason</th><td>{esc(reasons)}</td></tr>
  <tr><th>executed_order_count</th><td>{esc(core["executed_order_count"])}</td></tr>
  <tr><th>pending_order</th><td>{esc(json.dumps(core["pending_order"], ensure_ascii=False))}</td></tr>
  <tr><th>자동매매 ON/OFF</th><td>{esc(core["auto_trade_enabled"])}</td></tr>
  <tr><th>HOLD 상태</th><td>{esc(core["HOLD"])}</td></tr>
</table>
<p><button data-testid="final-order-button" {disabled} title="{esc(reasons)}">최종 승인 후 주문 실행</button></p>
<p><button data-testid="auto-trade-button" disabled title="자동매매는 재확인과 사용자 승인이 필요합니다.">자동매매 시작</button></p>
"""
    return html_page("Simon Orders", body)


def render_wall() -> bytes:
    status = build_status()
    body = f"""
<h1>큰 화면</h1>
{status_cards(status)}
<pre>{json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True)}</pre>
"""
    return html_page("Simon Wall", body)


class SimonHandler(BaseHTTPRequestHandler):
    server_version = "SimonOps/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def _send(self, payload: bytes, content_type: str = "text/html; charset=utf-8", status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        started = time.monotonic()
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/chat")
            self.end_headers()
            return
        if path == "/api/status":
            status = build_status()
            status["api_elapsed_seconds"] = round(time.monotonic() - started, 6)
            self._send(json_bytes(status), "application/json; charset=utf-8")
            return
        if path == "/chat":
            self._send(render_chat())
            return
        if path == "/dashboard/account":
            self._send(render_account())
            return
        if path == "/dashboard/market":
            self._send(render_market())
            return
        if path == "/dashboard/orders":
            self._send(render_orders())
            return
        if path == "/dashboard/wall":
            self._send(render_wall())
            return
        self._send(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/api/chat", "/api/resident/command"):
            self._send(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
            return
        data = self._read_json()
        text = str(data.get("message") or data.get("text") or "")
        route = route_voice_command(text)
        if route.get("pending_order_candidate"):
            notify("pending_order_created", route["message"], "warning", {"input": text}, popup=False)
        if route.get("auto_trade_candidate"):
            notify("auto_trade_approval_required", route["message"], "warning", {"input": text}, popup=False)
        response = {
            "ok": True,
            "route": route,
            "status": build_status(),
            "safety": {
                "executed_order_count": 0,
                "auto_trade_enabled": False,
                "HOLD": True,
                "broker_submit_called": False,
            },
        }
        self._send(json_bytes(response), "application/json; charset=utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simon P0 operations server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("STOCK_SERVER_PORT", "8080")))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_runtime_dir()
    server = ThreadingHTTPServer((args.host, args.port), SimonHandler)
    print(f"Simon ops server listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

