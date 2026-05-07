"""Merge curated QA hard-fail data before runtime intent errors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            if line.strip():
                yield json.loads(line)


def collect_logs(
    *,
    curated_path: Path = Path("data/curated/qa_intent_20000.jsonl"),
    intent_errors_path: Path = Path("data/intent_errors.jsonl"),
    output_path: Path = Path("data/curated/intent_training_merged.jsonl"),
) -> dict[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    synthetic_rows = list(iter_jsonl(curated_path) or [])
    error_rows = list(iter_jsonl(intent_errors_path) or [])
    rows.extend(synthetic_rows)
    rows.extend(error_rows)

    with output_path.open("w", encoding="utf-8") as output_file:
        for row in rows:
            output_file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "synthetic_qa_rows": len(synthetic_rows),
        "intent_error_rows": len(error_rows),
        "output_rows": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/curated/intent_training_merged.jsonl")
    args = parser.parse_args()
    print(json.dumps(collect_logs(output_path=Path(args.output)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
