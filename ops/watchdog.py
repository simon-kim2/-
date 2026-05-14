from __future__ import annotations

import argparse
import json
import time
import urllib.error
from typing import Any

from ops import launcher
from simon_ops.alerts import notify
from simon_ops.state import save_watchdog_state, utc_now


def _safe_status_for_log(status: dict[str, Any] | None) -> dict[str, Any] | None:
    if status is None:
        return None
    core = status.get("core", {})
    return {
        "health": status.get("health"),
        "server_pid": status.get("server_pid"),
        "price_feed_available": core.get("price_feed_available"),
        "market_data_limited": core.get("market_data_limited"),
        "executed_order_count": core.get("executed_order_count"),
        "auto_trade_enabled": core.get("auto_trade_enabled"),
        "HOLD": core.get("HOLD"),
    }


def check_once(port: int, restart: bool = False, target: str = "server") -> dict[str, Any]:
    checked_at = utc_now()
    try:
        status = launcher.fetch_status(port, timeout=3.0)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        state = save_watchdog_state(
            {
                "enabled": True,
                "running": True,
                "status": "server_down",
                "last_heartbeat_at": checked_at,
                "last_error": str(exc),
            }
        )
        notify("watchdog_server_down", f"/api/status 확인 실패: {exc}", "critical", state, popup=False)
        if restart:
            try:
                launcher.stop_existing()
                proc = launcher.start_process(target, port)
                recovered = launcher.wait_for_status(port, deadline_seconds=30.0)
            except Exception as restart_exc:
                state = save_watchdog_state(
                    {
                        "enabled": True,
                        "running": True,
                        "status": "restart_failed",
                        "last_heartbeat_at": utc_now(),
                        "last_error": str(restart_exc),
                    }
                )
                notify("watchdog_restart_failed", f"사이먼 서버 재시작 실패: {restart_exc}", "critical", state, popup=False)
                return state
            state = save_watchdog_state(
                {
                    "enabled": True,
                    "running": True,
                    "status": "restarted",
                    "last_heartbeat_at": utc_now(),
                    "last_status_ok_at": utc_now(),
                    "last_restart_at": utc_now(),
                    "restart_count": int(state.get("restart_count") or 0) + 1,
                    "last_error": None,
                    "last_restart_pid": proc.pid,
                    "last_status": _safe_status_for_log(recovered),
                }
            )
            notify("watchdog_server_restarted", f"사이먼 서버 재시작 PID={proc.pid}", "warning", state, popup=False)
        return state

    health = status.get("health")
    core = status.get("core", {})
    unsafe = core.get("executed_order_count", 0) != 0 or bool(core.get("auto_trade_enabled"))
    watchdog_status = "unsafe" if unsafe else "ok"
    if health == "degraded" and watchdog_status == "ok":
        watchdog_status = "degraded"
    state = save_watchdog_state(
        {
            "enabled": True,
            "running": True,
            "status": watchdog_status,
            "last_heartbeat_at": checked_at,
            "last_status_ok_at": checked_at if watchdog_status != "unsafe" else None,
            "last_error": None,
            "last_status": _safe_status_for_log(status),
        }
    )
    if watchdog_status == "unsafe":
        notify("watchdog_unsafe_state", "안전 불변식 위반 상태를 감지했습니다.", "critical", state, popup=False)
    elif watchdog_status == "degraded":
        notify("watchdog_degraded_state", "사이먼은 실행 중이지만 데이터/거래 준비 상태가 제한됩니다.", "warning", state, popup=False)
    return state


def run_loop(args: argparse.Namespace) -> int:
    while True:
        check_once(args.port, restart=not args.no_restart, target=args.target)
        if args.once:
            return 0
        time.sleep(args.interval)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simon P0 watchdog")
    parser.add_argument("--port", type=int, default=launcher.DEFAULT_PORT)
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--target", choices=("auto", "main", "server"), default="server")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-restart", action="store_true", help="Only record/alert status; do not restart a down server.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_loop(args)


if __name__ == "__main__":
    raise SystemExit(main())
