"""Build a hard-fail QA intent dataset for Simon NLU regression training."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


INTENT_TEMPLATES = {
    "stock_analysis": [
        "{stock} 지금 차트 어때?",
        "{stock} 오늘 들어가도 되는 자리야?",
        "{stock} 단기 흐름 분석해줘",
        "{stock} 사도 돼?",
    ],
    "theme_top": [
        "오늘 강한 국내 테마 알려줘",
        "상승 테마 순위 보여줘",
        "인기 테마 뭐야?",
    ],
    "us_theme_rank": [
        "나스닥 현재 인기 상승 테마 알려줘",
        "미국 증시 강세 테마 순위 보여줘",
        "nasdaq 상승 섹터 랭킹",
    ],
    "investor_rank": [
        "외국인 기관 수급 좋은 종목 순위",
        "기관 순매수 랭킹 알려줘",
        "외국인 매집 종목 보여줘",
    ],
    "cancel_pending": [
        "미체결 주문 취소할까?",
        "{stock} 미체결 취소 가능해?",
    ],
    "price_current": [
        "{stock} 현재가 알려줘",
        "{stock} 지금 가격 얼마야?",
    ],
    "value_metric_single": [
        "PBR 낮은 저평가 종목 찾아줘",
        "PER 낮은 가치주 순위 알려줘",
    ],
    "buy": [
        "{symbol} 10주 매수 승인 후 실행",
        "{symbol} 5주 사줘 승인 완료",
    ],
    "sell": [
        "{symbol} 10주 매도 승인 후 실행",
        "{symbol} 5주 팔아줘 승인 완료",
    ],
}

TARGET_COUNTS = {
    "stock_analysis": 3166,
    "theme_top": 1426,
    "us_theme_rank": 1357,
    "investor_rank": 1128,
    "cancel_pending": 825,
    "price_current": 539,
    "value_metric_single": 1059,
    "buy": 235,
    "sell": 265,
}

STOCKS = ["삼성전자", "SK하이닉스", "NAVER", "카카오", "현대차", "LG에너지솔루션"]
SYMBOLS = ["005930", "000660", "035420", "035720", "AAPL", "TSLA"]
QUESTION_MARKERS = ("?", "어때", "할까", "사도 돼", "가능", "알려줘", "보여줘")
ORDER_INTENTS = {"buy", "sell"}


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sequence = 0
    for intent, count in TARGET_COUNTS.items():
        templates = INTENT_TEMPLATES[intent]
        for index in range(count):
            stock = STOCKS[index % len(STOCKS)]
            symbol = SYMBOLS[index % len(SYMBOLS)]
            template = templates[index % len(templates)]
            text = template.format(stock=stock, symbol=symbol)
            rows.append(
                {
                    "id": f"qa-hardfail-{sequence:05d}",
                    "text": f"{text} #{sequence:05d}",
                    "intent": intent,
                    "critical": intent not in ORDER_INTENTS,
                    "source": "synthetic_hardfail",
                }
            )
            sequence += 1
    return rows


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    texts = [str(row["text"]) for row in rows]
    duplicate_count = len(texts) - len(set(texts))
    intent_counts = Counter(str(row["intent"]) for row in rows)
    question_order_contamination = sum(
        1
        for row in rows
        if str(row["intent"]) in ORDER_INTENTS
        and any(marker in str(row["text"]) for marker in QUESTION_MARKERS)
    )
    return {
        "rows": len(rows),
        "duplicate_count": duplicate_count,
        "duplicate_rate": duplicate_count / len(rows) if rows else 0.0,
        "question_to_order_contamination": {
            "count": question_order_contamination,
            "rate": question_order_contamination / len(rows) if rows else 0.0,
        },
        "critical_rate": sum(1 for row in rows if row["critical"]) / len(rows) if rows else 0.0,
        "max_single_intent_rate": max(intent_counts.values()) / len(rows) if rows else 0.0,
        "intent_distribution": dict(intent_counts),
    }


def quality_gate(report: dict[str, object]) -> bool:
    contamination = report["question_to_order_contamination"]
    assert isinstance(contamination, dict)
    return (
        report["rows"] == 10_000
        and report["duplicate_rate"] <= 0.01
        and contamination["rate"] == 0.0
        and report["critical_rate"] >= 0.20
        and report["max_single_intent_rate"] <= 0.35
    )


def write_outputs(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    report = summarize(rows)
    report["gate_passed"] = quality_gate(report)

    jsonl_path = output_dir / "qa_intent_20000.jsonl"
    csv_path = output_dir / "qa_intent_20000.csv"
    report_path = output_dir / "qa_intent_20000_report.json"

    with jsonl_path.open("w", encoding="utf-8") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["id", "text", "intent", "critical", "source"])
        writer.writeheader()
        writer.writerows(rows)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/curated")
    args = parser.parse_args()
    report = write_outputs(Path(args.output_dir))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
