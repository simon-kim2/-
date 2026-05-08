"""Daily Simon learning pipeline runner.

The pipeline can collect and evaluate NLU cases, but it never auto-promotes a
model. Promotion requires a separate manual approval and passing quality gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simon.learning.pipeline import ModelPromotionGate, TrainingPipeline
from tools.collect_logs import collect_logs


def run_daily() -> dict[str, object]:
    merge = collect_logs()
    pipeline = TrainingPipeline()
    cases = pipeline.load_error_cases("data/intent_errors.jsonl")
    metrics = pipeline.evaluate_cases(cases)
    decision = ModelPromotionGate().evaluate(metrics, manual_approval=False)
    return {
        "overall_status": "completed_with_hold",
        "gate_passed": decision.promoted,
        "promotion_reason": decision.reason,
        "collect_logs": merge,
        "metrics": {
            "accuracy": metrics.accuracy,
            "order_false_positive_rate": metrics.order_false_positive_rate,
            "total": metrics.total,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily"], default="daily")
    parser.add_argument("--output", default="data/pipeline_result.json")
    args = parser.parse_args()

    result = run_daily()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
