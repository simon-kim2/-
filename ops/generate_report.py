from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from simon_ops.state import RUNTIME_DIR, build_status, ensure_runtime_dir, utc_now


def _status_lines(status: dict[str, Any]) -> list[str]:
    core = status["core"]
    resident = status["resident"]
    watchdog = status["watchdog"]
    return [
        "# Simon P0 Operations Report",
        "",
        f"- generated_at: {status['generated_at']}",
        f"- status_schema: {status['status_schema_version']}",
        f"- view_model_schema: {status['view_model_schema']}",
        f"- health: {status['health']}",
        f"- safe_to_trade: {status['safe_to_trade']}",
        f"- server_pid: {status['server_pid']}",
        "",
        "## Safety invariants",
        "",
        f"- executed_order_count: {core['executed_order_count']}",
        f"- auto_trade_enabled: {core['auto_trade_enabled']}",
        f"- HOLD: {core['HOLD']}",
        f"- broker_submit_enabled: {core['broker_submit_enabled']}",
        f"- order_execution_enabled: {core['order_execution_enabled']}",
        f"- order_execution_block_reason: {', '.join(core['order_execution_block_reason'])}",
        "",
        "## Data and runtime",
        "",
        f"- price_feed_available: {core['price_feed_available']}",
        f"- current_price_source: {core['current_price_source']}",
        f"- stale_price: {core['stale_price']}",
        f"- market_data_limited: {core['market_data_limited']}",
        f"- resident_status: {resident['status']}",
        f"- resident_stt_available: {resident['stt_available']}",
        f"- watchdog_status: {watchdog['status']}",
        "",
        "## Result",
        "",
        "This report is an operational snapshot only. It does not certify live trading readiness.",
    ]


def write_report(output_dir: Path | None = None) -> dict[str, str]:
    ensure_runtime_dir()
    status = build_status()
    target_dir = output_dir or (RUNTIME_DIR / "reports")
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().replace(":", "").replace("-", "")
    json_path = target_dir / f"simon_p0_status_{stamp}.json"
    md_path = target_dir / f"simon_p0_status_{stamp}.md"
    json_path.write_text(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(_status_lines(status)) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Simon P0 operational status report")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = write_report(args.output_dir)
    print(json.dumps(paths, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
