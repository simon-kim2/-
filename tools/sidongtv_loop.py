"""SidongTV collection loop.

This loop is intentionally separated from main.py/server.py order execution.
Collected items are internal-only advisory signals and cannot trigger orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simon.source_policy import SIDONGTV_CHANNEL_ID, sidongtv_policy

KST = ZoneInfo("Asia/Seoul")


def current_phase(now: datetime | None = None) -> str:
    now = now or datetime.now(KST)
    hhmm = now.strftime("%H:%M")
    if "09:00" <= hhmm <= "15:30":
        return "market_collect_only"
    if "15:31" <= hhmm <= "23:59":
        return "after_market_collect_preprocess"
    return "night_collect_training_separated"


def run_once(log_path: Path = Path("data/sources/sidongwiki/logs/sidongtv_loop.jsonl")) -> dict[str, object]:
    policy = sidongtv_policy()
    event = {
        "created_at": datetime.now(KST).isoformat(),
        "channel_id": SIDONGTV_CHANNEL_ID,
        "phase": current_phase(),
        "signal_mode": "advisory_only",
        "internal_only": policy.internal_only,
        "no_redistribute": policy.no_redistribute,
        "order_trigger_allowed": policy.order_trigger_allowed,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not args.once:
        raise SystemExit("Use --once in this scaffold; schedule externally via tools/schedule_jobs.sh")
    print(json.dumps(run_once(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
